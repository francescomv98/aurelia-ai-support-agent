import re
import openai
from typing import Literal
from langchain_openai import ChatOpenAI
from langgraph.graph import START, END, StateGraph
from sqlalchemy.orm import Session
from src.agent.router import route_request
from src.agent.state import AgentState
from src.logging.logger import logger
from src.rag.rag_service import RAGService
from src.tools.machine_tools import get_machine_tool
from src.services.maintenance_service import calculate_maintenance_status
from src.tools.ticket_tools import get_machine_ticket_tool
from sqlalchemy import select
from src.database.models import Customer
from langgraph.checkpoint.postgres import PostgresSaver
from src.agent.action_preparation import prepare_action
from src.agent.human_approval import request_human_approval
from src.agent.authorization import authorize_action
from sqlalchemy.exc import SQLAlchemyError
from src.services.exceptions import DatabaseError, LLMError, AuthorizationError
from src.mcp.client import create_mcp_client, call_mcp_tool

def retrieve_context(state: AgentState, rag_service: RAGService) -> AgentState:
    """Retrieve relevant documentation for the user query."""
    logger.info("Retrieving context", query_length=len(state["user_query"]))
    
    try:
        context = rag_service.retrieve_context(state["user_query"])
    except DatabaseError:
        logger.exception("RAG retrieval unavailable")
        return {
            **state,
            "retrieved_context": [],
            "rag_available": False
        }

    return {
        **state,
        "retrieved_context": context,
        "rag_available": True
    }


def determine_tool_type(state: AgentState) -> AgentState:
    """Determine which enterprise tool is required."""
    query = state["user_query"].upper()

    product_match = re.search(r"\b(?:AIS-\d{3}|SP-[A-Z0-9-]+)\b", query.upper())
    customer_match = re.search(r"\bCUST-\d+\b", query.upper())

    if "ORD-" in query:
        tool_type = "order"
    elif "SHIP-" in query:
        tool_type = "shipment"
    elif ("AIS1-" in query or "AIS2-" in query or "AIS5-" in query):
        tool_type = "machine"
    elif product_match:
        tool_type = "product"
    elif customer_match:
        tool_type = "customer"
    else:
        tool_type = None

    logger.info("Enterprise tool type determined", tool_type=tool_type)

    return {
        **state,
        "tool_type": tool_type
    }


def human_approval(state: AgentState) -> AgentState:
    if state["pending_action"] is None:
        logger.error("Human approval requested without pending action")
        raise ValueError("No pending action available for human approval.")

    decision = request_human_approval(state["pending_action"])

    return {
        **state,
        "tool_result": (
            "The requested action was approved."
            if decision == "APPROVED"
            else "The requested action was rejected."
        )
    }


async def execute_tool(state: AgentState, db: Session, rag_service: RAGService) -> AgentState:
    """Execute the enterprise tool selected for the request."""
    logger.info("Executing agent tool", tool_type=state["tool_type"])

    user = state["authenticated_user"]

    query = state["user_query"]

    if state["tool_type"] == "order":
        order_id = None

        for word in query.split():
            if word.upper().startswith("ORD-"):
                order_id = word.strip(".,!?")
                break

        if order_id is None:
            return {
                **state,
                "tool_result": "I could not identify an order number."
            }

        if user.customer_id is None:
            raise AuthorizationError("Customer user has no customer context.")

        async with create_mcp_client() as client:
            result = await call_mcp_tool(client=client, tool_name="get_order_status_tool",
                arguments={
                    "order_id": order_id,
                    "customer_id": user.customer_id
                }
            )

        return {
            **state,
            "tool_result": result
        }

    if state["tool_type"] == "machine":
        machine_serial = None

        for word in query.split():
            normalized_word = word.strip(".,!?").upper()

            if normalized_word.startswith(("AIS1-", "AIS2-", "AIS5-")):
                machine_serial = normalized_word
                break

        if machine_serial is None:
            return {
                **state,
                "tool_result": "I could not identify a machine serial number."
            }

        if state["route"] == "tool":
            if user.customer_id is None:
                raise AuthorizationError("Customer user has no customer context.")

            query_lower = query.lower()

            maintenance_keywords = ("maintenance", "maintenance history", "maintenance record", "maintenance records", "service history",
                "service record", "service records")

            is_maintenance_request = any(keyword in query_lower for keyword in maintenance_keywords)

            if is_maintenance_request:
                async with create_mcp_client() as client:
                    result = await call_mcp_tool(client=client, tool_name="get_maintenance_history_tool",
                        arguments={
                            "machine_serial": machine_serial,
                            "customer_id": user.customer_id
                        }
                    )

                return {
                    **state,
                    "tool_result": result
                }

            ticket_keywords = ("ticket", "support ticket", "support case", "case")

            is_ticket_request = any(keyword in query_lower for keyword in ticket_keywords)

            if is_ticket_request:
                async with create_mcp_client() as client:
                    result = await call_mcp_tool(client=client, tool_name="get_support_ticket_tool",
                        arguments={
                            "machine_serial": machine_serial,
                            "customer_id": user.customer_id
                        }
                    )

                return {
                    **state,
                    "tool_result": result
                }

            async with create_mcp_client() as client:
                result = await call_mcp_tool(client=client, tool_name="get_machine_status_tool",
                    arguments={
                        "machine_serial": machine_serial,
                        "customer_id": user.customer_id
                    }
                )

            return {
                **state,
                "tool_result": result
            }

        machine_result = get_machine_tool(db=db, machine_serial=machine_serial, user=user)

        if machine_result.status == "NOT_FOUND":
            return {
                **state,
                "tool_result": machine_result.message
            }

        if state["route"] != "hybrid":
            return {
                **state,
                "tool_result": machine_result.message
            }

        # ------------------------------------------------------------------
        # Hybrid request: determine whether the user is asking about
        # maintenance or an existing support ticket.
        # ------------------------------------------------------------------

        query_lower = query.lower()

        ticket_keywords = ("ticket", "support ticket", "support case", "case")

        is_ticket_request = any(keyword in query_lower for keyword in ticket_keywords)

        if is_ticket_request:
            ticket_result = get_machine_ticket_tool(db=db, machine_serial=machine_serial, user=user)

            return {
                **state,
                "tool_result": (
                    f"{machine_result.message} "
                    f"{ticket_result.message}"
                )
            }

        # ------------------------------------------------------------------
        # Hybrid maintenance request
        # ------------------------------------------------------------------

        if (machine_result.model is None or machine_result.operating_hours is None):
            logger.error("Machine data incomplete", machine_serial=machine_result.machine_serial)

            return {
                **state,
                "tool_result": "Machine information is incomplete and maintenance status cannot be calculated."
            }

        maintenance_interval = rag_service.extract_maintenance_interval(documents=state["retrieved_context"], model=machine_result.model)

        if maintenance_interval is None:
            logger.warning("Maintenance interval unavailable from RAG", machine_serial=machine_result.machine_serial, model=machine_result.model)

            return {
                **state,
                "tool_result": (
                    f"{machine_result.message} "
                    "The current maintenance interval could not be determined from the available documentation."
                )
            }

        maintenance_result = calculate_maintenance_status(current_hours=machine_result.operating_hours, maintenance_interval=maintenance_interval)

        tool_result = (
            f"{machine_result.message} "
            f"{maintenance_result.message}"
        )

        return {
            **state,
            "tool_result": tool_result
        }

    if state["tool_type"] == "shipment":
        tracking_match = re.search(r"\bSHIP-\d+\b", state["user_query"].upper())

        if not tracking_match:
            logger.warning("Shipment tracking number not found in query")
            return {
                **state,
                "tool_result": "Shipment tracking number not found."
            }

        tracking_number = tracking_match.group(0)

        if user.customer_id is None:
            raise AuthorizationError("Customer user has no customer context.")

        async with create_mcp_client() as client:
            result = await call_mcp_tool(client=client, tool_name="track_shipment_tool",
                arguments={
                    "tracking_number": tracking_number,
                    "customer_id": user.customer_id
                }
            )

        return {
            **state,
            "tool_result": result
        }

    if state["tool_type"] == "product":
        product_match = re.search(r"\b(?:AIS-\d{3}|SP-[A-Z0-9-]+)\b", query.upper())

        if not product_match:
            return {
                **state,
                "tool_result": "I could not identify a product code."
            }

        product_code = product_match.group(0)

        async with create_mcp_client() as client:
            result = await call_mcp_tool(client=client, tool_name="get_product_tool",
                arguments={
                    "product_code": product_code
               }
            )

        return {
            **state,
            "tool_result": result
        }
    
    if state["tool_type"] == "customer":
        customer_match = re.search(r"\bCUST-\d+\b", query.upper())

        if not customer_match:
            customer_id = user.customer_id
            if customer_id is None:
                raise AuthorizationError("Customer user has no customer context.")
        else:
            customer_code = customer_match.group(0)

            try:
                customer = db.scalar(select(Customer).where(Customer.customer_code == customer_code))
            except SQLAlchemyError as exc:
                logger.exception("Database operation failed")
                raise DatabaseError("Database operation failed.") from exc

            if customer is None:
                return {
                    **state,
                    "tool_result": "The requested customer was not found."
                }

            customer_id = customer.id

        async with create_mcp_client() as client:
            result = await call_mcp_tool(client=client, tool_name="get_customer_tool",
                arguments={ "customer_id": customer_id }
            )

        return {**state, "tool_result": result}

    logger.warning("No enterprise tool selected")

    return {
        **state,
        "tool_result": ("No suitable enterprise tool was identified.")
    }


async def execute_write_tool(state: AgentState, db: Session) -> AgentState:
    pending_action = state["pending_action"]

    if pending_action is None:
        logger.error("Write tool execution requested without pending action")
        raise ValueError("No pending action available for write execution.")

    logger.info("Executing approved write action", action_type=pending_action.action_type)

    if pending_action.action_type == "create_order":
        user = state["authenticated_user"]

        if user.customer_id is None:
            raise AuthorizationError("Authenticated user has no customer context.")

        async with create_mcp_client() as client:
            result = await call_mcp_tool(client=client, tool_name="create_order_tool",
                arguments={
                    "customer_id": user.customer_id,
                    "items": pending_action.parameters.get("items", [])
                }
            )

        return {
            **state,
            "tool_result": result
        }

    if pending_action.action_type == "cancel_order":
        order_number = pending_action.parameters.get("order_number")

        if not order_number:
            raise ValueError("Order number is required for cancel_order.")

        user = state["authenticated_user"]

        if user.customer_id is None:
            raise AuthorizationError("Authenticated user has no customer context.")

        async with create_mcp_client() as client:
            result = await call_mcp_tool(client=client, tool_name="cancel_order_tool",
                arguments={
                    "order_id": order_number,
                    "customer_id": user.customer_id
                }
            )

        return {
            **state,
            "tool_result": result
        }

    if pending_action.action_type == "create_support_ticket":
        user = state["authenticated_user"]

        if user.customer_id is None:
            raise AuthorizationError("Authenticated user has no customer context.")

        async with create_mcp_client() as client:
            result = await call_mcp_tool(client=client, tool_name="create_support_ticket_tool",
                arguments={
                    "customer_id": user.customer_id,
                    "category": pending_action.parameters["category"],
                    "priority": pending_action.parameters["priority"],
                    "subject": pending_action.parameters["subject"],
                    "description": pending_action.parameters["description"],
                    "machine_serial": pending_action.parameters.get("machine_serial")
                }
            )

        return {
            **state,
            "tool_result": result
        }

    if pending_action.action_type == "update_support_ticket":
        user = state["authenticated_user"]

        if user.customer_id is None:
            raise AuthorizationError("Authenticated user has no customer context.")

        async with create_mcp_client() as client:
            result = await call_mcp_tool(client=client, tool_name="update_support_ticket_tool",
                arguments={
                    "ticket_number": pending_action.parameters["ticket_number"],
                    "customer_id": user.customer_id,
                    "status": pending_action.parameters.get("status"),
                    "priority": pending_action.parameters.get("priority"),
                    "subject": pending_action.parameters.get("subject"),
                    "description": pending_action.parameters.get("description")
                }
            )

        return {
            **state,
            "tool_result": result
        }

    raise ValueError(f"Unsupported write action: {pending_action.action_type}")


def generate_response(state: AgentState, chat_model: ChatOpenAI, rag_service: RAGService) -> AgentState:
    """Generate the final response using retrieved context and/or tool results."""
    logger.info("Generating agent response")

    context_sections = []

    if state["route"] == "rag" and not state["rag_available"]:
        logger.warning("RAG unavailable for RAG-only request")

        return {
            **state,
            "response": ("I'm sorry, but the documentation service is currently unavailable. Please try again later.")
        }

    if state["retrieved_context"]:
        documentation_context = rag_service.build_context(state["retrieved_context"])

        context_sections.append(
            f"DOCUMENTATION CONTEXT:\n"
            f"{documentation_context}"
        )

    if state["tool_result"]:
        context_sections.append(
            f"ENTERPRISE TOOL RESULT:\n"
            f"{state['tool_result']}"
        )

    context = "\n\n".join(context_sections)

    prompt = f"""
You are the customer support assistant for Aurelia Industrial Systems.

Answer the customer's question using only the information provided
in the context below.

If enterprise tool data is available, treat it as authoritative for
the requested enterprise operation.

Do not invent information.

When the documentation contains safety warnings, prohibitions,
mandatory instructions, thresholds, or other safety constraints,
preserve them explicitly in your answer when they are relevant
to the customer's question.

Do not omit, weaken, or contradict safety-critical instructions.
Prioritize safety-critical instructions over brevity.

Customer question:
{state["user_query"]}

Context:
{context}
"""

    try:
        response = chat_model.invoke(prompt)
    except openai.APITimeoutError as exc:
        logger.exception("LLM request timed out")
        raise LLMError("The AI service timed out.") from exc

    return {
        **state,
        "response": response.content
    }


def route_after_retrieval(state: AgentState) -> Literal["generate_response", "determine_tool_type"]:
    """Determine the next step after documentation retrieval."""
    if state["route"] == "rag":
        return "generate_response"

    return "determine_tool_type"


async def execute_tool_node(state: AgentState, db: Session, rag_service: RAGService) -> AgentState:
    return await execute_tool(state, db, rag_service)


def build_agent_graph(chat_model: ChatOpenAI, rag_service: RAGService, db: Session, checkpointer: PostgresSaver):
    """Build the Aurelia support agent graph."""

    async def execute_tool_graph_node(state: AgentState) -> AgentState:
        return await execute_tool_node(state, db, rag_service)
    
    async def execute_write_tool_graph_node(state: AgentState) -> AgentState:
        return await execute_write_tool(state, db)
    
    graph = StateGraph(AgentState)

    graph.add_node("route_request", lambda state: route_request(state, chat_model))
    graph.add_node("retrieve_context", lambda state: retrieve_context(state, rag_service))
    graph.add_node("determine_tool_type", determine_tool_type)
    graph.add_node("prepare_action", lambda state: prepare_action(state, chat_model))
    graph.add_node("human_approval", human_approval)
    graph.add_node("authorize_action", authorize_action)
    graph.add_node("execute_tool", execute_tool_graph_node)
    graph.add_node("execute_write_tool", execute_write_tool_graph_node)
    graph.add_node("generate_response", lambda state: generate_response(state, chat_model, rag_service))
                   
    graph.add_conditional_edges(
        "route_request",
        lambda state: state["route"],
        {
            "rag": "retrieve_context",
            "tool": "determine_tool_type",
            "hybrid": "retrieve_context"
        }
    )

    graph.add_conditional_edges(
        "retrieve_context",
        route_after_retrieval,
        {
            "generate_response": "generate_response",
            "determine_tool_type": "determine_tool_type"
        }
    )

    
    graph.add_conditional_edges(
        "prepare_action",
        lambda state: (
            "human_approval"
            if state["pending_action"] is not None
            else "execute_tool"
        ),
        {
            "human_approval": "human_approval",
            "execute_tool": "execute_tool"
        }
    )

    graph.add_conditional_edges(
        "human_approval",
        lambda state: (
            "authorize_action"
            if state["tool_result"] == "The requested action was approved."
            else "generate_response"
        ),
        {
            "authorize_action": "authorize_action",
            "generate_response": "generate_response"
        }
    )

    graph.add_edge(START, "route_request")
    graph.add_edge("authorize_action", "execute_write_tool")
    graph.add_edge("execute_write_tool", "generate_response")
    graph.add_edge("determine_tool_type", "prepare_action")    
    graph.add_edge("execute_tool", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile(checkpointer=checkpointer)
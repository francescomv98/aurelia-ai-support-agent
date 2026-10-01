from typing import Literal
from langchain_openai import ChatOpenAI
from langgraph.graph import START, END, StateGraph
from sqlalchemy.orm import Session
from src.agent.router import route_request
from src.agent.state import AgentState
from src.logging.logger import logger
from src.rag.rag_service import RAGService
from src.tools.machine_tools import get_machine_tool
from src.tools.order_tools import get_order_status_tool
from src.services.maintenance_service import calculate_maintenance_status
from src.tools.ticket_tools import get_machine_ticket_tool
from src.tools.shipment_tools import get_shipment_tool
from src.tools.product_tools import get_product_tool
from src.tools.customer_tools import get_customer_tool
import re
from sqlalchemy import select
from src.database.models import Customer

def retrieve_context(state: AgentState, rag_service: RAGService) -> AgentState:
    """Retrieve relevant documentation for the user query."""
    logger.info("Retrieving context", query_length=len(state["user_query"]))

    context = rag_service.retrieve_context(state["user_query"])

    return {
        **state,
        "retrieved_context": context
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


def execute_tool(state: AgentState, db: Session, rag_service: RAGService) -> AgentState:
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
                "tool_result": ("I could not identify an order number.")
            }

        result = get_order_status_tool(db=db, order_id=order_id, user=user)

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
                "tool_result": (
                    "Machine information is incomplete and maintenance status cannot be calculated."
                )
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

        shipment_result = get_shipment_tool(db=db, tracking_number=tracking_number, user=state["authenticated_user"])

        return {
            **state,
            "tool_result": shipment_result.message
        }

    if state["tool_type"] == "product":
        product_match = re.search(r"\b(?:AIS-\d{3}|SP-[A-Z0-9-]+)\b", query.upper())

        if not product_match:
            return {
                **state,
                "tool_result": "I could not identify a product code."
            }

        product_code = product_match.group(0)

        product_result = get_product_tool(db=db, product_code=product_code, user=user)

        return {
            **state,
            "tool_result": product_result.message
        }
    
    if state["tool_type"] == "customer":
        customer_match = re.search(r"\bCUST-\d+\b", query.upper())

        customer_id = None

        if customer_match:
            customer_code = customer_match.group(0)

            customer = db.scalar(select(Customer).where(Customer.customer_code == customer_code))

            if customer is None:
                return {
                    **state,
                    "tool_result": "The requested customer was not found."
                }

            customer_id = customer.id

        customer_result = get_customer_tool(db=db, user=user, customer_id=customer_id)

        return {
            **state,
            "tool_result": customer_result.message
        }

    logger.warning("No enterprise tool selected")

    return {
        **state,
        "tool_result": ("No suitable enterprise tool was identified.")
    }


def generate_response(state: AgentState, chat_model: ChatOpenAI, rag_service: RAGService) -> AgentState:
    """Generate the final response using retrieved context and/or tool results."""
    logger.info("Generating agent response")

    context_sections = []

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

Customer question:
{state["user_query"]}

Context:
{context}
"""

    response = chat_model.invoke(prompt)

    return {
        **state,
        "response": response.content
    }


def route_after_retrieval(state: AgentState) -> Literal["generate_response", "determine_tool_type"]:
    """Determine the next step after documentation retrieval."""
    if state["route"] == "rag":
        return "generate_response"

    return "determine_tool_type"


def build_agent_graph(chat_model: ChatOpenAI, rag_service: RAGService, db: Session):
    """Build the Aurelia support agent graph."""

    graph = StateGraph(AgentState)

    graph.add_node("route_request", lambda state: route_request(state, chat_model))
    graph.add_node("retrieve_context", lambda state: retrieve_context(state, rag_service))
    graph.add_node("determine_tool_type", determine_tool_type)
    graph.add_node("execute_tool", lambda state: execute_tool(state, db, rag_service))
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

    graph.add_edge(START, "route_request")
    graph.add_edge("determine_tool_type", "execute_tool")
    graph.add_edge("execute_tool", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()
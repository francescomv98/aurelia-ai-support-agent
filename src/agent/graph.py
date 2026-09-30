from collections.abc import Callable
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session
from src.agent.router import route_request
from src.agent.state import AgentState
from src.logging.logger import logger
from src.rag.rag_service import RAGService
from src.tools.order_tools import get_order_status_tool
from src.tools.machine_tools import get_machine_tool

def retrieve_context(state: AgentState, rag_service: RAGService) -> AgentState:
    """Retrieve relevant documentation for the user query."""
    logger.info("Retrieving context", query_length=len(state["user_query"]))

    context = rag_service.retrieve_context(state["user_query"])

    return {
        **state,
        "retrieved_context": context
    }


def execute_tool(state: AgentState, db: Session) -> AgentState:
    """Execute the enterprise tool selected for the request."""
    logger.info("Executing agent tool", tool_type=state["tool_type"])

    if state["customer_id"] is None:
        logger.warning("Tool execution rejected: missing customer context")

        return {
            **state,
            "tool_result": (
                "Customer context is required to access "
                "enterprise information."
            )
        }

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

        result = get_order_status_tool(db=db, order_id=order_id, customer_id=state["customer_id"])

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
                "tool_result": (
                    "I could not identify a machine serial number."
                )
            }

        result = get_machine_tool(db=db, machine_serial=machine_serial, customer_id=state["customer_id"])

        return {
            **state,
            "tool_result": result
        }

    logger.warning("No enterprise tool selected")

    return {
        **state,
        "tool_result": "No suitable enterprise tool was identified."
    }


def generate_response(state: AgentState, chat_model: ChatOpenAI) -> AgentState:
    """Generate the final response using retrieved context and/or tool results."""
    logger.info("Generating agent response")

    context_sections = []

    if state["retrieved_context"]:
        context_sections.append(f"DOCUMENTATION CONTEXT:\n{state['retrieved_context']}")

    if state["tool_result"]:
        context_sections.append(f"ENTERPRISE TOOL RESULT:\n{state['tool_result']}")

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


def build_agent_graph(chat_model: ChatOpenAI, rag_service: RAGService, db: Session):
    """Build the Aurelia support agent graph."""

    graph = StateGraph(AgentState)

    graph.add_node("determine_tool_type", determine_tool_type)
    graph.add_node("execute_tool", lambda state: execute_tool(state, db))

    graph.add_edge("retrieve_context", "determine_tool_type")
    graph.add_edge("determine_tool_type", "execute_tool")
    graph.add_edge("execute_tool", "generate_response")

    graph.add_conditional_edges(
        "route_request",
        lambda state: state["route"],
        {
            "rag": "retrieve_context",
            "tool": "determine_tool_type",
            "hybrid": "retrieve_context"
        }
    )

    return graph.compile()


def determine_tool_type(state: AgentState) -> AgentState:
    """Determine which enterprise tool is required."""
    query = state["user_query"].upper()

    if "ORD-" in query:
        tool_type = "order"
    elif "AIS1-" in query or "AIS2-" in query or "AIS5-" in query:
        tool_type = "machine"
    else:
        tool_type = None

    logger.info("Enterprise tool type determined", tool_type=tool_type)

    return {
        **state,
        "tool_type": tool_type
    }
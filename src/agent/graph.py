from collections.abc import Callable
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session
from src.agent.router import route_request
from src.agent.state import AgentState
from src.logging.logger import logger
from src.rag.rag_service import RAGService
from src.tools.order_tools import get_order_status_tool

def retrieve_context(state: AgentState, rag_service: RAGService) -> AgentState:
    """Retrieve relevant documentation for the user query."""
    logger.info("Retrieving context", query_length=len(state["user_query"]))

    context = rag_service.retrieve_context(state["user_query"])

    return {
        **state,
        "retrieved_context": context
    }


def execute_tool(state: AgentState, db: Session) -> AgentState:
    """Execute the enterprise tool selected by the agent."""
    logger.info("Executing agent tool", route=state["route"])

    query = state["user_query"]

    order_id = None

    words = query.split()

    for word in words:
        if word.startswith("ORD-"):
            order_id = word.strip(".,!?")

            break

    if order_id is None:
        logger.info("No order identifier found in tool request")

        return {
            **state,
            "tool_result": "I could not identify an order number in the request."
        }

    if state["customer_id"] is None:
        logger.warning("Tool execution rejected: missing customer context")

        return {
            **state,
            "tool_result": "Customer context is required to access order information."
        }

    result = get_order_status_tool(db=db, order_id=order_id, customer_id=state["customer_id"])

    return {
        **state,
        "tool_result": result
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

    graph.add_node("route_request", lambda state: route_request(state, chat_model))
    graph.add_node("retrieve_context", lambda state: retrieve_context(state, rag_service))
    graph.add_node("execute_tool", lambda state: execute_tool(state, db))
    graph.add_node("generate_response", lambda state: generate_response(state, chat_model))

    graph.add_edge(START, "route_request")
    graph.add_conditional_edges(
        "route_request",
        lambda state: state["route"],
        {
            "rag": "retrieve_context",
            "hybrid": "retrieve_context",
            "tool": "execute_tool"
        }
    )
    graph.add_edge("retrieve_context", "generate_response")
    graph.add_edge("execute_tool", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()
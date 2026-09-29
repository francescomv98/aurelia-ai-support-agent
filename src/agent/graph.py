from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from src.agent.router import route_request
from src.agent.state import AgentState
from src.logging.logger import logger
from src.rag.rag_service import RAGService


def retrieve_context(
    state: AgentState,
    rag_service: RAGService,
) -> AgentState:
    """Retrieve relevant context for the user's request."""

    logger.info(
        "Retrieving context for agent request",
        query_length=len(state["user_query"]),
    )

    documents = rag_service.retrieve_context(
        state["user_query"],
    )

    context = rag_service.build_context(documents)

    logger.info(
        "Agent context retrieval completed",
        document_count=len(documents),
        context_length=len(context),
    )

    return {
        **state,
        "retrieved_context": context,
    }


def generate_response(
    state: AgentState,
    chat_model: ChatOpenAI,
) -> AgentState:
    """Generate a response using the available context."""

    logger.info("Generating agent response")

    prompt = f"""
You are the AI support assistant for Aurelia Industrial Systems.

Answer the user's question using the provided context.

If the available context does not contain enough information,
clearly state that you do not have enough information.

Do not invent technical, contractual, operational, or
customer-specific information.

User question:
{state["user_query"]}

Context:
{state["retrieved_context"]}
"""

    try:
        result = chat_model.invoke(prompt)

        response = result.content

        logger.info(
            "Agent response generated",
            response_length=len(response),
        )

        return {
            **state,
            "response": response,
        }

    except Exception:
        logger.exception("Failed to generate agent response")
        raise


def select_next_node(state: AgentState) -> str:
    """Select the next node based on the routing decision."""

    return state["route"]


def build_agent_graph(
    rag_service: RAGService,
    chat_model: ChatOpenAI,
):
    """Build the support agent graph."""

    logger.info("Building support agent graph")

    graph = StateGraph(AgentState)

    graph.add_node(
        "route_request",
        lambda state: route_request(
            state,
            chat_model,
        ),
    )

    graph.add_node(
        "retrieve_context",
        lambda state: retrieve_context(
            state,
            rag_service,
        ),
    )

    graph.add_node(
        "generate_response",
        lambda state: generate_response(
            state,
            chat_model,
        ),
    )

    graph.add_edge(
        START,
        "route_request",
    )

    graph.add_conditional_edges(
        "route_request",
        select_next_node,
        {
            "rag": "retrieve_context",
            "tool": "generate_response",
            "hybrid": "retrieve_context",
        },
    )

    graph.add_edge(
        "retrieve_context",
        "generate_response",
    )

    graph.add_edge(
        "generate_response",
        END,
    )

    return graph.compile()
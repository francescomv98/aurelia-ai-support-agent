from typing import Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from src.agent.state import AgentState
from src.logging.logger import logger

class RouteDecision(BaseModel):
    """Structured decision produced by the agent router."""

    route: Literal["rag", "tool", "hybrid"] = Field(
        description=(
            "Route to use: rag for documentation questions, "
            "tool for enterprise data operations, "
            "hybrid when both documentation and enterprise data are required."
        )
    )


def route_request(state: AgentState, chat_model: ChatOpenAI) -> AgentState:
    """Determine how the user's request should be handled."""

    logger.info("Routing agent request", query_length=len(state["user_query"]))

    router_model = chat_model.with_structured_output(RouteDecision)

    prompt = f"""
You are the routing component of the Aurelia Industrial Systems
customer support agent.

Determine which information source is required to answer the user's request.

Available routes:

- rag:
  Use when the answer can be obtained from Aurelia's documentation,
  manuals, technical specifications, policies, FAQs, or maintenance
  documentation.

- tool:
  Use when the request requires customer-specific or operational data
  from enterprise systems, such as orders, shipments, machines,
  maintenance records, or support tickets.

- hybrid:
  Use when answering the request requires both enterprise data and
  information from Aurelia's documentation.

Examples:

"What is the maximum speed of the AIS-200?"
→ rag

"What is the status of order ORD-10245?"
→ tool

"Does my machine need maintenance?"
→ hybrid

"I have error E-204; what should I do and do I already have a support ticket?"
→ hybrid

User request:
{state["user_query"]}
"""

    try:
        decision = router_model.invoke(prompt)

        logger.info("Agent request routed", route=decision.route)

        return {
            **state,
            "route": decision.route
        }

    except Exception:
        logger.exception("Failed to route agent request")
        raise
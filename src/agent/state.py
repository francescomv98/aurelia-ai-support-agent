from typing import Literal, TypedDict

class AgentState(TypedDict):
    """State shared across the support agent graph."""

    user_query: str
    route: Literal["rag", "tool", "hybrid"]
    retrieved_context: str
    response: str
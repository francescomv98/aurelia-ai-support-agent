from typing import Literal, TypedDict

class AgentState(TypedDict):
    """State shared across the support agent graph."""

    user_query: str
    customer_id: int | None
    route: Literal["rag", "tool", "hybrid"]
    retrieved_context: str
    tool_result: str
    response: str
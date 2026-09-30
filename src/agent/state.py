from typing import Literal, TypedDict
from langchain_core.documents import Document

class AgentState(TypedDict):
    """State shared across the support agent graph."""

    user_query: str
    customer_id: int | None
    route: Literal["rag", "tool", "hybrid"]
    retrieved_context: list[Document]
    tool_type: Literal["order", "machine"] | None
    tool_result: str
    response: str
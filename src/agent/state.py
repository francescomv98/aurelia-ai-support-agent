from typing import Literal, TypedDict
from langchain_core.documents import Document
from src.auth.models import AuthenticatedUser

class AgentState(TypedDict):
    """State shared across the support agent graph."""

    user_query: str
    authenticated_user: AuthenticatedUser
    route: Literal["rag", "tool", "hybrid"]
    retrieved_context: list[Document]
    tool_type: Literal["order", "machine", "shipment", "product", "customer"] | None
    tool_result: str
    response: str
from typing import Literal, TypedDict
from langchain_core.documents import Document
from src.auth.models import AuthenticatedUser
from pydantic import BaseModel

class PendingAction(BaseModel):
    action_type: Literal["create_order", "cancel_order", "create_support_ticket", "update_support_ticket"]
    description: str
    parameters: dict


class AgentState(TypedDict):
    """State shared across the support agent graph."""

    user_query: str
    authenticated_user: AuthenticatedUser
    route: Literal["rag", "tool", "hybrid"]
    retrieved_context: list[Document]
    rag_available: bool
    tool_type: Literal["order", "machine", "shipment", "product", "customer"] | None
    pending_action: PendingAction | None
    tool_result: str
    response: str
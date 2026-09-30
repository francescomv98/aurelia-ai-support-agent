from pydantic import BaseModel
from src.database.models import UserRole

class AuthenticatedUser(BaseModel):
    """Identity and security context of an authenticated user."""

    user_id: int
    customer_id: int | None
    role: UserRole
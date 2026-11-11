from collections.abc import Collection
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.app_logging.logger import logger
from src.services.exceptions import AuthorizationError

def require_role(user: AuthenticatedUser, allowed_roles: Collection[UserRole]) -> None:
    """Ensure the authenticated user has one of the required roles."""

    if user.role not in allowed_roles:
        logger.warning("Authorization denied: insufficient role", user_id=user.user_id, role=user.role.value)
        raise AuthorizationError("User is not authorized for this operation.")


def require_customer_access(user: AuthenticatedUser, customer_id: int) -> None:
    """Ensure the user is authorized to access a customer resource."""

    if user.role in { UserRole.SUPPORT_AGENT, UserRole.ADMIN }:
        return

    if user.role == UserRole.CUSTOMER and user.customer_id == customer_id:
        return

    logger.warning("Authorization denied: customer access violation", user_id=user.user_id, role=user.role.value)
    raise AuthorizationError("User is not authorized to access this customer.")
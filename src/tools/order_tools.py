from sqlalchemy.orm import Session
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.logging.logger import logger
from src.security.authorization import require_customer_access
from src.services.order_service import get_order_status

def get_order_status_tool(db: Session, order_id: str, user: AuthenticatedUser, customer_id: int | None = None,) -> str:
    """Retrieve an order status after authorization."""

    logger.info("Executing order status tool", order_id=order_id, user_id=user.user_id)

    if user.role == UserRole.CUSTOMER:
        if user.customer_id is None:
            raise PermissionError("Customer user has no customer context.")

        target_customer_id = user.customer_id
    else:
        if customer_id is None:
            raise ValueError("Customer ID is required for internal users.")

        target_customer_id = customer_id

    require_customer_access(user, target_customer_id)

    result = get_order_status(db=db, order_id=order_id, customer_id=user.customer_id)

    return result.message
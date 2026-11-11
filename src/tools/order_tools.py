from sqlalchemy.orm import Session
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.app_logging.logger import logger
from src.security.authorization import require_customer_access
from src.services.order_service import (CreateOrderResult, OrderItemRequest, CancelOrderResult, cancel_order, create_order, get_order_status)
from src.services.exceptions import AuthorizationError, ValidationError

def get_order_status_tool(db: Session, order_id: str, user: AuthenticatedUser, customer_id: int | None = None,) -> str:
    """Retrieve an order status after authorization."""

    logger.info("Executing order status tool", order_id=order_id, user_id=user.user_id)

    if user.role == UserRole.CUSTOMER:
        if user.customer_id is None:
            raise AuthorizationError("Customer user has no customer context.")

        target_customer_id = user.customer_id
    else:
        if customer_id is None:
            raise ValidationError("Customer ID is required for internal users.")

        target_customer_id = customer_id

    require_customer_access(user, target_customer_id)

    result = get_order_status(db=db, order_id=order_id, customer_id=target_customer_id)

    return result.message


def create_order_tool(db, user: AuthenticatedUser, items: list[OrderItemRequest], customer_id: int | None = None) -> CreateOrderResult:
    """Create an order for an authorized customer."""

    if user.role.value == "CUSTOMER":
        if user.customer_id is None:
            raise AuthorizationError("Customer user is not associated with a customer.")

        if customer_id is not None and customer_id != user.customer_id:
            raise AuthorizationError("Customer users cannot create orders for another customer.")

        target_customer_id = user.customer_id

    else:
        if customer_id is None:
            raise ValidationError("Customer ID is required for internal users.")

        target_customer_id = customer_id

    require_customer_access(user, target_customer_id)

    return create_order(db=db, customer_id=target_customer_id, items=items)


def cancel_order_tool(db, order_id: str, user: AuthenticatedUser, customer_id: int | None = None) -> CancelOrderResult:
    """Cancel an order for an authorized customer."""

    if user.role.value == "CUSTOMER":
        if user.customer_id is None:
            raise AuthorizationError("Customer user is not associated with a customer.")

        if customer_id is not None and customer_id != user.customer_id:
            raise AuthorizationError("Customer users cannot cancel orders for another customer.")

        target_customer_id = user.customer_id

    else:
        if customer_id is None:
            raise ValidationError("Customer ID is required for internal users.")

        target_customer_id = customer_id

    require_customer_access(user, target_customer_id)

    return cancel_order(db=db, order_id=order_id, customer_id=target_customer_id)
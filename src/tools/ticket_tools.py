from sqlalchemy.orm import Session
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.logging.logger import logger
from src.security.authorization import require_customer_access
from src.services.ticket_service import TicketResult, get_machine_ticket
from src.services.exceptions import AuthorizationError, ValidationError

def get_machine_ticket_tool(db: Session, machine_serial: str, user: AuthenticatedUser, customer_id: int | None = None) -> TicketResult:
    """Retrieve a machine support ticket after authorization."""

    logger.info("Executing support ticket tool", machine_serial=machine_serial, user_id=user.user_id)

    if user.role == UserRole.CUSTOMER:
        if user.customer_id is None:
            raise AuthorizationError("Customer user has no customer context.")

        target_customer_id = user.customer_id
    else:
        if customer_id is None:
            raise ValidationError("Customer ID is required for internal users.")

        target_customer_id = customer_id

    require_customer_access(user, target_customer_id)

    return get_machine_ticket(db=db, machine_serial=machine_serial, customer_id=target_customer_id)
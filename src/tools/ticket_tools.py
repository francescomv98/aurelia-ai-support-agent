from sqlalchemy.orm import Session
from src.auth.models import AuthenticatedUser
from src.app_logging.logger import logger
from src.security.authorization import require_customer_access
from src.services.ticket_service import TicketResult, get_machine_ticket
from src.services.exceptions import AuthorizationError

def get_machine_ticket_tool(db: Session, machine_serial: str, user: AuthenticatedUser) -> TicketResult:
    """Retrieve the support ticket of a machine owned by the authenticated customer."""

    logger.info("Executing support ticket tool", machine_serial=machine_serial, user_id=user.user_id)

    if user.customer_id is None:
        raise AuthorizationError("Customer user has no customer context.")

    require_customer_access(user, user.customer_id)

    return get_machine_ticket(db=db, machine_serial=machine_serial, customer_id=user.customer_id)

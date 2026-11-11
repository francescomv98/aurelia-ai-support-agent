from sqlalchemy.orm import Session
from src.auth.models import AuthenticatedUser
from src.app_logging.logger import logger
from src.security.authorization import require_customer_access
from src.services.machine_service import MachineResult, get_machine
from src.services.exceptions import AuthorizationError

def get_machine_tool(db: Session, machine_serial: str, user: AuthenticatedUser) -> MachineResult:
    """Retrieve a machine owned by the authenticated customer."""

    logger.info("Executing machine information tool", machine_serial=machine_serial, user_id=user.user_id)

    if user.customer_id is None:
        raise AuthorizationError("Customer user has no customer context.")

    require_customer_access(user, user.customer_id)

    return get_machine(db=db, machine_serial=machine_serial, customer_id=user.customer_id)

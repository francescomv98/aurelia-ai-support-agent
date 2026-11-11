from sqlalchemy.orm import Session
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.app_logging.logger import logger
from src.security.authorization import require_customer_access
from src.services.machine_service import MachineResult, get_machine
from src.services.exceptions import AuthorizationError, ValidationError

def get_machine_tool(db: Session, machine_serial: str, user: AuthenticatedUser, customer_id: int | None = None) -> MachineResult:
    """Retrieve machine information after authorization."""

    logger.info("Executing machine information tool", machine_serial=machine_serial, user_id=user.user_id)

    if user.role == UserRole.CUSTOMER:
        if user.customer_id is None:
            raise AuthorizationError("Customer user has no customer context.")

        target_customer_id = user.customer_id
    else:
        if customer_id is None:
            raise ValidationError("Customer ID is required for internal users.")

        target_customer_id = customer_id

    require_customer_access(user, target_customer_id)

    return get_machine(db=db, machine_serial=machine_serial, customer_id=target_customer_id)
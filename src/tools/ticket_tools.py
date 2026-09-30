from sqlalchemy.orm import Session
from src.logging.logger import logger
from src.services.ticket_service import TicketResult, get_machine_ticket

def get_machine_ticket_tool(db: Session, machine_serial: str, customer_id: int) -> TicketResult:
    """Retrieve the support ticket associated with a machine."""

    logger.info("Executing support ticket tool", machine_serial=machine_serial)

    return get_machine_ticket(db=db, machine_serial=machine_serial, customer_id=customer_id)
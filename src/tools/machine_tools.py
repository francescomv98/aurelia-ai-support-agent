from sqlalchemy.orm import Session
from src.logging.logger import logger
from src.services.machine_service import MachineResult, get_machine

def get_machine_tool(db: Session, machine_serial: str, customer_id: int) -> MachineResult:
    """Retrieve machine information for the agent."""

    logger.info("Executing machine information tool", machine_serial=machine_serial)

    return get_machine(db=db, machine_serial=machine_serial, customer_id=customer_id)
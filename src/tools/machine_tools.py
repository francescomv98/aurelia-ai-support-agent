from sqlalchemy.orm import Session
from src.logging.logger import logger
from src.services.machine_service import get_machine

def get_machine_tool(db: Session, machine_serial: str, customer_id: int) -> str:
    """Retrieve machine information for the authenticated customer."""
    logger.info("Executing machine information tool", machine_serial=machine_serial)

    result = get_machine(db=db, machine_serial=machine_serial, customer_id=customer_id)

    if result["status"] == "NOT_FOUND":
        return result["message"]

    return (
        f"Machine {result['machine_serial']} "
        f"is an {result['model']} with "
        f"{result['operating_hours']} operating hours."
    )
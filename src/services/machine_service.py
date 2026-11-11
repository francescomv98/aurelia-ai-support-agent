from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.database.models import Machine
from src.app_logging.logger import logger
from typing import Literal
from pydantic import BaseModel
from src.services.exceptions import DatabaseError

class MachineResult(BaseModel):
    """Result returned by the machine service."""

    status: Literal["FOUND", "NOT_FOUND"]
    machine_serial: str | None = None
    model: str | None = None
    operating_hours: int | None = None
    message: str
    
    
def get_machine(db: Session, machine_serial: str, customer_id: int) -> MachineResult:
    """Retrieve a machine belonging to the authenticated customer."""
    logger.info("Retrieving machine", machine_serial=machine_serial)

    try:
        machine = db.scalar(select(Machine).where(Machine.serial_number == machine_serial, Machine.customer_id == customer_id))

        if machine is None:
            logger.info("Machine not found for customer", machine_serial=machine_serial)

            return MachineResult(
                status="NOT_FOUND",
                message="Machine not found."
            )

        logger.info("Machine retrieved", machine_serial=machine_serial)

        return MachineResult(
            status="FOUND",
            machine_serial=machine.serial_number,
            model=machine.product.name,
            operating_hours=machine.operating_hours,
            message=(
                f"Machine {machine.serial_number} is an "
                f"{machine.product.name} with "
                f"{machine.operating_hours} operating hours."
            )
        )

    except SQLAlchemyError as exc:
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc  
    except Exception:
        logger.exception("Failed to retrieve machine", machine_serial=machine_serial)
        raise
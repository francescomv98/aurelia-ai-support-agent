from typing import Literal
from pydantic import BaseModel
from src.logging.logger import logger
from src.services.exceptions import ValidationError
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from src.database.models import MaintenanceRecord, Machine
from src.services.exceptions import DatabaseError

class MaintenanceResult(BaseModel):
    """Result returned by the maintenance calculation service."""

    status: Literal["OVERDUE", "NOT_DUE"]
    current_hours: int
    maintenance_interval: int
    remaining_hours: int | None
    message: str


class MaintenanceHistoryResult(BaseModel):
    """Result returned by the maintenance history service."""

    status: Literal["FOUND", "NOT_FOUND"]
    machine_serial: str | None = None
    records: list[str] = []
    message: str


def calculate_maintenance_status(current_hours: int, maintenance_interval: int) -> MaintenanceResult:
    """Calculate whether machine maintenance is due."""

    logger.info("Calculating maintenance status", current_hours=current_hours, maintenance_interval=maintenance_interval)

    if current_hours < 0:
        raise ValidationError("Current operating hours cannot be negative.")

    if maintenance_interval <= 0:
        raise ValidationError("Maintenance interval must be greater than zero.")

    if current_hours >= maintenance_interval:
        result = MaintenanceResult(
            status="OVERDUE",
            current_hours=current_hours,
            maintenance_interval=maintenance_interval,
            remaining_hours=None,
            message=(
                f"Maintenance is overdue. "
                f"The machine has {current_hours} operating hours "
                f"and the maintenance interval is "
                f"{maintenance_interval} hours."
            )
        )

        logger.info("Maintenance is overdue", current_hours=current_hours, maintenance_interval=maintenance_interval)

        return result

    remaining_hours = maintenance_interval - current_hours

    result = MaintenanceResult(
        status="NOT_DUE",
        current_hours=current_hours,
        maintenance_interval=maintenance_interval,
        remaining_hours=remaining_hours,
        message=(
            f"Maintenance is not yet due. "
            f"The machine has {current_hours} operating hours "
            f"and {remaining_hours} hours remain until maintenance."
        )
    )

    logger.info("Maintenance is not yet due", remaining_hours=remaining_hours)

    return result


def get_maintenance_history(db: Session, machine_serial: str, customer_id: int) -> MaintenanceHistoryResult:
    """Retrieve the maintenance history of a machine belonging to the customer."""

    logger.info("Retrieving maintenance history", machine_serial=machine_serial, customer_id=customer_id)

    try:
        machine = db.scalar(select(Machine).where(Machine.serial_number == machine_serial, Machine.customer_id == customer_id))

        if machine is None:
            logger.info("Machine not found for customer", machine_serial=machine_serial, customer_id=customer_id)

            return MaintenanceHistoryResult(
                status="NOT_FOUND",
                message="Machine not found."
            )

        maintenance_records = db.scalars(select(MaintenanceRecord).where(MaintenanceRecord.machine_id == machine.id)
            .order_by(MaintenanceRecord.performed_at.desc())).all()

    except SQLAlchemyError as exc:
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc

    if not maintenance_records:
        logger.info("No maintenance records found", machine_serial=machine_serial)

        return MaintenanceHistoryResult(
            status="NOT_FOUND",
            machine_serial=machine.serial_number,
            message=f"No maintenance records were found for machine {machine.serial_number}."
        )

    records = [
        (
            f"{record.maintenance_type.value} maintenance performed on "
            f"{record.performed_at.isoformat()}. "
            f"Operating hours: {record.operating_hours}. "
            f"Notes: {record.notes or 'none'}."
        )
        for record in maintenance_records
    ]

    logger.info("Maintenance history retrieved", machine_serial=machine.serial_number, record_count=len(records))

    return MaintenanceHistoryResult(
        status="FOUND",
        machine_serial=machine.serial_number,
        records=records,
        message=(
            f"Maintenance history for machine "
            f"{machine.serial_number}: "
            + " ".join(records)
        )
    )
from typing import Literal
from pydantic import BaseModel
from src.logging.logger import logger

class MaintenanceResult(BaseModel):
    """Result returned by the maintenance calculation service."""

    status: Literal["OVERDUE", "NOT_DUE"]
    current_hours: int
    maintenance_interval: int
    remaining_hours: int | None
    message: str


def calculate_maintenance_status(current_hours: int, maintenance_interval: int) -> MaintenanceResult:
    """Calculate whether machine maintenance is due."""

    logger.info("Calculating maintenance status", current_hours=current_hours, maintenance_interval=maintenance_interval)

    if current_hours < 0:
        raise ValueError("Current operating hours cannot be negative.")

    if maintenance_interval <= 0:
        raise ValueError("Maintenance interval must be greater than zero.")

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
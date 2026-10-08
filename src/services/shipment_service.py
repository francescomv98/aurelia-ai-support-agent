from datetime import datetime
from typing import Literal
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.database.models import Order, Shipment
from src.logging.logger import logger
from src.services.exceptions import DatabaseError

class ShipmentResult(BaseModel):
    status: Literal["FOUND", "NOT_FOUND"]
    tracking_number: str | None
    carrier: str | None
    shipment_status: str | None
    estimated_delivery: datetime | None
    message: str


def get_shipment(db: Session, tracking_number: str, customer_id: int) -> ShipmentResult:
    try:
        shipment = db.scalar(
            select(Shipment)
            .join(Order, Shipment.order_id == Order.id)
            .where(Shipment.tracking_number == tracking_number, Order.customer_id == customer_id)
        )
    except SQLAlchemyError as exc:
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc  

    if shipment is None:
        logger.info("Shipment not found", tracking_number=tracking_number, customer_id=customer_id)

        return ShipmentResult(
            status="NOT_FOUND",
            tracking_number=None,
            carrier=None,
            shipment_status=None,
            estimated_delivery=None,
            message=f"The shipment {tracking_number} was not found in the system."
        )

    logger.info("Shipment retrieved", tracking_number=tracking_number, customer_id=customer_id)

    return ShipmentResult(
        status="FOUND",
        tracking_number=shipment.tracking_number,
        carrier=shipment.carrier,
        shipment_status=shipment.status.value,
        estimated_delivery=shipment.estimated_delivery,
        message=(
            f"Shipment {shipment.tracking_number} is currently "
            f"{shipment.status.value}. "
            f"Carrier: {shipment.carrier}. "
            f"Estimated delivery: "
            f"{shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else 'not available'}."
        )
    )
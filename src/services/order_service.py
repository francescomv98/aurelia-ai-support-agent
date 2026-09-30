from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database.models import Order
from typing import Literal
from pydantic import BaseModel
from src.logging.logger import logger

class OrderResult(BaseModel):
    """Result returned by the order service."""

    status: Literal["FOUND", "NOT_FOUND"]
    order_status: str | None = None
    message: str

def get_order_status(db: Session, order_id: str, customer_id: int) -> dict[str, str]:
    """Retrieve an order status for an authorized customer."""

    logger.info("Retrieving order status", order_id=order_id)

    try:
        statement = select(Order).where(
            Order.order_number == order_id,
            Order.customer_id == customer_id
        )

        order = db.scalar(statement)

        if order is None:
            logger.info("Order not found for customer", order_id=order_id)

            return OrderResult(
                status="NOT_FOUND",
                message="Order not found."
            )

        logger.info("Order status retrieved", order_id=order_id, status=order.status)

        return OrderResult(
            status="FOUND",
            order_status=str(order.status),
            message=f"Order {order_id} is {order.status}."
        )

    except Exception:
        logger.exception("Failed to retrieve order status", order_id=order_id)
        raise
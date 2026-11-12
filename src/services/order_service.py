from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from src.database.models import Order, OrderItem, Product
from typing import Literal
from pydantic import BaseModel
from src.app_logging.logger import logger
from decimal import Decimal
from datetime import datetime, timezone
from src.services.exceptions import ValidationError, DatabaseError

ORDER_NUMBER_ATTEMPTS = 3

class OrderResult(BaseModel):
    """Result returned by the order service."""

    status: Literal["FOUND", "NOT_FOUND"]
    order_status: str | None = None
    message: str


class OrderItemRequest(BaseModel):
    product_code: str
    quantity: int


class CreateOrderResult(BaseModel):
    status: str
    order_number: str | None
    message: str


class CancelOrderResult(BaseModel):
    """Result returned when cancelling an order."""
    status: Literal["CANCELLED", "NOT_FOUND", "NOT_CANCELLABLE"]
    order_number: str | None
    message: str


PRODUCT_PRICES = {
    "PROD-100": Decimal("85000.00"),
    "PROD-200": Decimal("135000.00"),
    "PROD-500": Decimal("245000.00"),
    "SP-204": Decimal("1850.00"),
    "SP-COOL-01": Decimal("1250.00"),
    "SP-SENSOR-02": Decimal("340.00")
}


PRODUCT_CODE_ALIASES = {
    "AIS-100": "PROD-100",
    "AIS-200": "PROD-200",
    "AIS-500": "PROD-500"
}


def get_order_status(db: Session, order_id: str, customer_id: int) -> OrderResult:
    """Retrieve an order status for an authorized customer."""

    logger.info("Retrieving order status", order_id=order_id)

    try:
        order = db.scalar(select(Order).where(Order.order_number == order_id, Order.customer_id == customer_id))

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

    except SQLAlchemyError as exc:
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc  
    except Exception:
        logger.exception("Failed to retrieve order status", order_id=order_id)
        raise


def create_order(db: Session, customer_id: int, items: list[OrderItemRequest]) -> CreateOrderResult:
    """Create a new order for a customer."""

    if not items:
        raise ValidationError("At least one order item is required.")

    for item in items:
        if item.quantity <= 0:
            raise ValidationError("Order item quantity must be greater than zero.")

    try:
        normalized_items: list[tuple[Product, int, Decimal]] = []

        for item in items:
            product_code = PRODUCT_CODE_ALIASES.get(item.product_code.upper(), item.product_code.upper())

            product = db.scalar(select(Product).where(Product.product_code == product_code))

            if product is None:
                return CreateOrderResult(
                    status="FAILED",
                    order_number=None,
                    message=f"The product {item.product_code} was not found in the catalog."
                )

            unit_price = PRODUCT_PRICES.get(product.product_code)

            if unit_price is None:
                return CreateOrderResult(
                    status="FAILED",
                    order_number=None,
                    message=f"No price is available for product {item.product_code}."
                )

            normalized_items.append((product, item.quantity, unit_price))

        # Order numbers are derived from the current maximum, so two concurrent
        # requests can pick the same one. The unique constraint catches that;
        # retry with a fresh number instead of failing the request.
        for attempt in range(1, ORDER_NUMBER_ATTEMPTS + 1):
            existing_orders = db.scalars(select(Order.order_number)).all()

            order_numbers = [
                int(order_number.removeprefix("ORD-"))
                for order_number in existing_orders
                if order_number.startswith("ORD-")
                and order_number.removeprefix("ORD-").isdigit()
            ]

            next_order_number = max(order_numbers, default=10240) + 1
            order_number = f"ORD-{next_order_number}"

            order = Order(
                order_number=order_number,
                status="PENDING",
                customer_id=customer_id,
                order_date=datetime.now(timezone.utc)
            )

            try:
                db.add(order)
                db.flush()

                order_items = [
                    OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=quantity,
                        unit_price=unit_price
                    )
                    for product, quantity, unit_price in normalized_items
                ]

                db.add_all(order_items)
                db.commit()
                break

            except IntegrityError:
                db.rollback()

                if attempt == ORDER_NUMBER_ATTEMPTS:
                    raise

                logger.warning("Order number collision, retrying", order_number=order_number, attempt=attempt)

        logger.info("Order created", order_number=order_number, customer_id=customer_id, item_count=len(order_items))

        return CreateOrderResult(
            status="CREATED",
            order_number=order_number,
            message=f"Order {order_number} was created successfully."
        )

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc  
    except Exception:
        db.rollback()
        logger.exception("Failed to create order", customer_id=customer_id)
        raise


def cancel_order(db: Session, order_id: str, customer_id: int) -> CancelOrderResult:
    """Cancel an order for an authorized customer."""

    logger.info("Cancelling order", order_id=order_id, customer_id=customer_id)

    try:
        order = db.scalar(select(Order).where(Order.order_number == order_id, Order.customer_id == customer_id)) 

        if order is None:
            logger.info("Order not found for customer", order_id=order_id, customer_id=customer_id)

            return CancelOrderResult(
                status="NOT_FOUND",
                order_number=None,
                message="Order not found."
            )

        current_status = (order.status.value if hasattr(order.status, "value") else order.status)

        cancellable_statuses = { "PENDING", "CONFIRMED", "PROCESSING" }

        if current_status not in cancellable_statuses:
            logger.info("Order cannot be cancelled", order_id=order_id, status=current_status)

            return CancelOrderResult(
                status="NOT_CANCELLABLE",
                order_number=order.order_number,
                message=f"Order {order_id} cannot be cancelled because it is currently {current_status}."
            )

        order.status = "CANCELLED"
        db.commit()

        logger.info("Order cancelled", order_id=order_id, customer_id=customer_id)

        return CancelOrderResult(
            status="CANCELLED",
            order_number=order.order_number,
            message=f"Order {order_id} was cancelled successfully."
        )
       
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc  
    except Exception:
        db.rollback()
        logger.exception("Failed to cancel order", order_id=order_id, customer_id=customer_id)
        raise
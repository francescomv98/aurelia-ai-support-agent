from sqlalchemy.orm import Session
from src.logging.logger import logger
from src.services.order_service import get_order_status

def get_order_status_tool(db: Session, order_id: str, customer_id: int) -> str:
    """Return the status of an order belonging to the customer."""

    logger.info("Executing order status tool", order_id=order_id)

    result = get_order_status(db=db, order_id=order_id, customer_id=customer_id)

    return result["message"]
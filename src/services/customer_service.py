from typing import Literal
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database.models import Customer
from src.logging.logger import logger

class CustomerResult(BaseModel):
    status: Literal["FOUND", "NOT_FOUND"]
    customer_code: str | None
    name: str | None
    industry: str | None
    country: str | None
    message: str


def get_customer(db: Session, customer_id: int) -> CustomerResult:
    """Retrieve customer information from the database."""

    customer = db.scalar(select(Customer).where(Customer.id == customer_id))

    if customer is None:
        logger.info("Customer not found", customer_id=customer_id)

        return CustomerResult(
            status="NOT_FOUND",
            customer_code=None,
            name=None,
            industry=None,
            country=None,
            message="The customer was not found in the system."
        )

    logger.info("Customer retrieved", customer_id=customer.id)

    return CustomerResult(
        status="FOUND",
        customer_code=customer.customer_code,
        name=customer.name,
        industry=customer.industry,
        country=customer.country,
        message=(
            f"Customer {customer.customer_code}: "
            f"{customer.name}. "
            f"Industry: {customer.industry}. "
            f"Country: {customer.country}."
        )
    )
from typing import Literal
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.database.models import Product
from src.logging.logger import logger
from src.services.exceptions import DatabaseError

class ProductResult(BaseModel):
    status: Literal["FOUND", "NOT_FOUND"]
    product_code: str | None
    name: str | None
    category: str | None
    capacity_per_minute: int | None
    maintenance_interval_hours: int | None
    message: str


def get_product(db: Session, product_code: str) -> ProductResult:
    """Retrieve product information from the database."""

    try:
        product = db.scalar(select(Product).where((Product.product_code == product_code) | (Product.name == product_code)))    
    except SQLAlchemyError as exc:
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc  

    if product is None:
        logger.info("Product not found", product_code=product_code)

        return ProductResult(
            status="NOT_FOUND",
            product_code=None,
            name=None,
            category=None,
            capacity_per_minute=None,
            maintenance_interval_hours=None,
            message=f"The product {product_code} was not found in the system."
        )

    logger.info("Product retrieved", product_code=product.product_code)

    return ProductResult(
        status="FOUND",
        product_code=product.product_code,
        name=product.name,
        category=product.category,
        capacity_per_minute=product.capacity_per_minute,
        maintenance_interval_hours=product.maintenance_interval_hours,
        message=(
            f"Product {product.product_code}: "
            f"{product.name}. "
            f"Category: {product.category}. "
            f"Capacity: "
            f"{product.capacity_per_minute} units per minute. "
            f"Maintenance interval: "
            f"{product.maintenance_interval_hours} operating hours."
        )
    )
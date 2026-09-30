import pytest
from sqlalchemy import select
from src.database.models import Customer, Order
from src.database.session import SessionLocal
from src.services.order_service import get_order_status

@pytest.mark.integration
def test_customer_can_access_own_order() -> None:
    with SessionLocal() as db:
        customer = db.scalar(select(Customer).where(Customer.customer_code == "CUST-001"))

        assert customer is not None

        result = get_order_status(db=db, order_id="ORD-10245", customer_id=customer.id)

        assert result["status"] == "SHIPPED"


@pytest.mark.integration
def test_customer_cannot_access_another_customer_order() -> None:
    with SessionLocal() as db:
        customer = db.scalar(select(Customer).where(Customer.customer_code == "CUST-002"))

        assert customer is not None

        result = get_order_status(db=db, order_id="ORD-10245", customer_id=customer.id)

        assert result["status"] == "NOT_FOUND"
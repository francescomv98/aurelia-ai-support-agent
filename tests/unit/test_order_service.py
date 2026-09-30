from types import SimpleNamespace
from src.services.order_service import get_order_status

class FakeSession:
    """Fake SQLAlchemy session for order service tests."""

    def __init__(self, order=None) -> None:
        self.order = order

    def scalar(self, statement):
        return self.order


def test_get_order_status() -> None:
    order = SimpleNamespace(order_number="ORD-10245", customer_id=1, status="SHIPPED")

    db = FakeSession(order)

    result = get_order_status(db=db, order_id="ORD-10245", customer_id=1)

    assert result["status"] == "SHIPPED"
    assert "ORD-10245" in result["message"]


def test_get_order_status_not_found() -> None:
    db = FakeSession(None)

    result = get_order_status(db=db, order_id="ORD-99999", customer_id=1)

    assert result["status"] == "NOT_FOUND"
    assert result["message"] == "Order not found."
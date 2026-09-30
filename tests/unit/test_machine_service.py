from src.services.order_service import OrderResult, get_order_status

class FakeSession:
    def __init__(self, order=None):
        self.order = order

    def scalar(self, statement):
        return self.order


class FakeOrder:
    status = "SHIPPED"


def test_get_order_status_returns_order() -> None:
    db = FakeSession(FakeOrder())

    result = get_order_status(db=db, order_id="ORD-10245", customer_id=1)

    assert isinstance(result, OrderResult)
    assert result.status == "FOUND"
    assert result.order_status == "SHIPPED"
    assert result.message == "Order ORD-10245 is SHIPPED."


def test_get_order_status_returns_not_found() -> None:
    db = FakeSession()

    result = get_order_status(db=db, order_id="ORD-10245", customer_id=1)

    assert isinstance(result, OrderResult)
    assert result.status == "NOT_FOUND"
    assert result.order_status is None
    assert result.message == "Order not found."
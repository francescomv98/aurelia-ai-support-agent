from decimal import Decimal
import pytest
from src.services.order_service import (CreateOrderResult, OrderItemRequest, OrderResult, create_order, get_order_status, cancel_order)
from datetime import datetime, timezone
from unittest.mock import patch
from src.database.models import Order

class FakeSession:
    def __init__(self, order=None, products=None, existing_order_numbers=None):
        self.order = order
        self.products = products or {}
        self.existing_order_numbers = existing_order_numbers or []
        self.added = []
        self.committed = False
        self.rolled_back = False

    def scalar(self, statement):
        statement_text = str(statement)

        if "products.product_code" in statement_text:
            product_code = statement.compile().params.get("product_code_1")
            return self.products.get(product_code)

        return self.order

    def scalars(self, statement):
        return FakeScalarResult(self.existing_order_numbers)

    def add(self, entity):
        self.added.append(entity)

    def add_all(self, entities):
        self.added.extend(entities)

    def flush(self):
        if self.added:
            order = self.added[0]

            if hasattr(order, "id") and order.id is None:
                order.id = 100

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def refresh(self):
        return None


class FakeScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeOrder:
    def __init__(self, order_number="ORD-20001", status="SHIPPED", customer_id=1):
        self.order_number = order_number
        self.status = status
        self.customer_id = customer_id


class FakeProduct:
    def __init__(self, product_id, product_code):
        self.id = product_id
        self.product_code = product_code


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


def test_create_order_creates_order_and_items() -> None:
    products = {
        "PROD-200": FakeProduct(1, "PROD-200"),
        "SP-204": FakeProduct(2, "SP-204")
    }

    db = FakeSession(
        products=products,
        existing_order_numbers=[
            "ORD-10241",
            "ORD-10242",
            "ORD-10243",
            "ORD-10244",
            "ORD-10245"
        ]
    )

    items = [
        OrderItemRequest(product_code="AIS-200", quantity=2),
        OrderItemRequest(product_code="SP-204", quantity=4)
    ]

    result = create_order(db=db, customer_id=1, items=items)

    assert isinstance(result, CreateOrderResult)
    assert result.status == "CREATED"
    assert result.order_number == "ORD-10246"
    assert result.message == "Order ORD-10246 was created successfully."

    assert db.committed is True
    assert db.rolled_back is False
    assert len(db.added) == 3

    order = db.added[0]

    assert order.order_number == "ORD-10246"
    assert order.status == "PENDING"
    assert order.customer_id == 1

    order_items = db.added[1:]

    assert len(order_items) == 2

    assert order_items[0].product_id == 1
    assert order_items[0].quantity == 2
    assert order_items[0].unit_price == Decimal("135000.00")

    assert order_items[1].product_id == 2
    assert order_items[1].quantity == 4
    assert order_items[1].unit_price == Decimal("1850.00")


def test_create_order_supports_product_alias() -> None:
    products = {
        "PROD-200": FakeProduct(1, "PROD-200")
    }

    db = FakeSession(products=products)

    result = create_order(db=db, customer_id=1,
        items=[
            OrderItemRequest(
                product_code="AIS-200",
                quantity=1
            )
        ]
    )

    assert result.status == "CREATED"
    assert result.order_number == "ORD-10241"

    order_item = db.added[1]

    assert order_item.product_id == 1
    assert order_item.quantity == 1
    assert order_item.unit_price == Decimal("135000.00")


def test_create_order_returns_failed_for_unknown_product() -> None:
    db = FakeSession(products={})

    result = create_order(db=db, customer_id=1,
        items=[
            OrderItemRequest(
                product_code="SP-UNKNOWN",
                quantity=1
            )
        ]
    )

    assert result.status == "FAILED"
    assert result.order_number is None
    assert "was not found in the catalog" in result.message
    assert db.committed is False


def test_create_order_returns_failed_when_price_is_unavailable() -> None:
    products = {
        "SP-100": FakeProduct(1, "SP-100")
    }

    db = FakeSession(products=products)

    result = create_order(db=db, customer_id=1,
        items=[
            OrderItemRequest(
                product_code="SP-100",
                quantity=1
            )
        ]
    )

    assert result.status == "FAILED"
    assert result.order_number is None
    assert "No price is available" in result.message
    assert db.committed is False


def test_create_order_rejects_empty_items() -> None:
    db = FakeSession()

    with pytest.raises(ValueError, match="At least one order item is required"):
        create_order(db=db, customer_id=1, items=[])


def test_create_order_rejects_invalid_quantity() -> None:
    db = FakeSession()

    with pytest.raises(ValueError, match="Order item quantity must be greater than zero"):
        create_order(db=db, customer_id=1,
            items=[
                OrderItemRequest(
                    product_code="AIS-200",
                    quantity=0
                )
            ]
        )


def test_create_order_rolls_back_on_database_error() -> None:
    class FailingSession(FakeSession):
        def commit(self):
            raise RuntimeError("Database error")

    products = { "PROD-200": FakeProduct(1, "PROD-200") }

    db = FailingSession(products=products)

    with pytest.raises(RuntimeError, match="Database error"):
        create_order(db=db, customer_id=1,
            items=[
                OrderItemRequest(
                    product_code="AIS-200",
                    quantity=1
                )
            ]
        )

    assert db.committed is False
    assert db.rolled_back is True


def test_cancel_order_success() -> None:
    order = FakeOrder(
        order_number="ORD-20001",
        status="PENDING",
        customer_id=1
    )

    db = FakeSession(order=order)

    result = cancel_order(db=db, order_id="ORD-20001", customer_id=1)

    assert result.status == "CANCELLED"
    assert result.order_number == "ORD-20001"
    assert "cancelled successfully" in result.message.lower()

    assert db.committed is True
    assert db.rolled_back is False
    assert order.status == "CANCELLED"


def test_cancel_order_not_found() -> None:
    db = FakeSession()

    result = cancel_order(db=db, order_id="ORD-99999", customer_id=1)

    assert result.status == "NOT_FOUND"
    assert result.order_number is None
    assert db.committed is False


@pytest.mark.parametrize("order_status", ["SHIPPED", "DELIVERED", "CANCELLED"])
def test_cancel_order_not_cancellable(order_status: str) -> None:
    order = FakeOrder(
        order_number="ORD-20001",
        status=order_status,
        customer_id=1
    )

    db = FakeSession(order=order)

    result = cancel_order(db=db, order_id="ORD-20001", customer_id=1)

    assert result.status == "NOT_CANCELLABLE"
    assert result.order_number == "ORD-20001"
    assert order.status == order_status
    assert db.committed is False


def test_cancel_order_rolls_back_on_database_error() -> None:
    class FailingSession(FakeSession):
        def commit(self):
            raise RuntimeError("Database error")

    order = FakeOrder(
        order_number="ORD-20002",
        status="PENDING",
        customer_id=1
    )

    db = FailingSession(order=order)

    with pytest.raises(RuntimeError, match="Database error"):
        cancel_order(db=db, order_id="ORD-20002", customer_id=1)

    assert db.committed is False
    assert db.rolled_back is True
from unittest.mock import Mock, patch
import pytest
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.services.order_service import CreateOrderResult, OrderItemRequest, CancelOrderResult
from src.tools.order_tools import create_order_tool, cancel_order_tool

def test_create_order_tool_customer_uses_own_customer_context() -> None:
    db = Mock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    items = [
        OrderItemRequest(
            product_code="AIS-200",
            quantity=2
        )
    ]

    expected_result = CreateOrderResult(
        status="CREATED",
        order_number="ORD-10246",
        message="Order ORD-10246 was created successfully."
    )

    with patch("src.tools.order_tools.create_order", return_value=expected_result) as create_order_mock:
        result = create_order_tool(db=db, user=user, items=items)

    assert result == expected_result

    create_order_mock.assert_called_once_with(db=db, customer_id=1, items=items)


def test_create_order_tool_customer_cannot_override_customer_context() -> None:
    db = Mock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    items = [
        OrderItemRequest(
            product_code="AIS-200",
            quantity=1
        )
    ]

    with pytest.raises(PermissionError):
        create_order_tool(db=db, user=user, items=items, customer_id=2)


def test_create_order_tool_customer_without_customer_context_is_rejected() -> None:
    db = Mock()

    user = AuthenticatedUser(user_id=1, customer_id=None, role=UserRole.CUSTOMER)

    items = [
        OrderItemRequest(
            product_code="AIS-200",
            quantity=1
        )
    ]

    with pytest.raises(PermissionError, match="Customer user is not associated with a customer"):
        create_order_tool(db=db, user=user, items=items)


def test_create_order_tool_support_agent_requires_customer_id() -> None:
    db = Mock()

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    items = [
        OrderItemRequest(
            product_code="AIS-200",
            quantity=1
        )
    ]

    with pytest.raises(ValueError, match="Customer ID is required for internal users"):
        create_order_tool(db=db, user=user, items=items)


def test_create_order_tool_support_agent_can_create_for_customer() -> None:
    db = Mock()

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    items = [
        OrderItemRequest(
            product_code="AIS-200",
            quantity=2
        ),
        OrderItemRequest(
            product_code="SP-204",
            quantity=4
        )
    ]

    expected_result = CreateOrderResult(
        status="CREATED",
        order_number="ORD-10246",
        message="Order ORD-10246 was created successfully."
    )

    with patch("src.tools.order_tools.create_order", return_value=expected_result) as create_order_mock:
        result = create_order_tool(db=db, user=user, items=items, customer_id=1)

    assert result == expected_result

    create_order_mock.assert_called_once_with(db=db, customer_id=1, items=items)


def test_create_order_tool_admin_can_create_for_customer() -> None:
    db = Mock()

    user = AuthenticatedUser(user_id=20, customer_id=None, role=UserRole.ADMIN)

    items = [
        OrderItemRequest(
            product_code="SP-204",
            quantity=2
        )
    ]

    expected_result = CreateOrderResult(
        status="CREATED",
        order_number="ORD-10247",
        message="Order ORD-10247 was created successfully."
    )

    with patch("src.tools.order_tools.create_order", return_value=expected_result) as create_order_mock:
        result = create_order_tool(db=db, user=user, items=items, customer_id=1)

    assert result == expected_result

    create_order_mock.assert_called_once_with(db=db, customer_id=1, items=items)


def test_cancel_order_tool_customer_uses_own_customer_context():
    db = Mock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    expected = CancelOrderResult(
        status="CANCELLED",
        order_number="ORD-20001",
        message="Order ORD-20001 was cancelled successfully."
    )

    with patch("src.tools.order_tools.cancel_order", return_value=expected) as mock_cancel:
        result = cancel_order_tool(db=db, order_id="ORD-20001", user=user)

    assert result == expected

    mock_cancel.assert_called_once_with(db=db, order_id="ORD-20001", customer_id=1)


def test_cancel_order_tool_customer_without_context():
    db = Mock()

    user = AuthenticatedUser(user_id=1, customer_id=None, role=UserRole.CUSTOMER)

    with pytest.raises(PermissionError, match="not associated with a customer"):
        cancel_order_tool(db=db, order_id="ORD-20001", user=user)


def test_cancel_order_tool_support_agent_requires_customer_id():
    db = Mock()

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    with pytest.raises(ValueError, match="Customer ID is required"):
        cancel_order_tool(db=db, order_id="ORD-20001", user=user)


def test_cancel_order_tool_support_agent_can_cancel_for_customer():
    db = Mock()

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    expected = CancelOrderResult(
        status="CANCELLED",
        order_number="ORD-20001",
        message="Order ORD-20001 was cancelled successfully."
    )

    with patch("src.tools.order_tools.cancel_order", return_value=expected) as mock_cancel:
        result = cancel_order_tool(db=db, order_id="ORD-20001", user=user, customer_id=1)

    assert result == expected

    mock_cancel.assert_called_once_with(db=db, order_id="ORD-20001", customer_id=1)


def test_cancel_order_tool_admin_can_cancel_for_customer():
    db = Mock()

    user = AuthenticatedUser(user_id=20, customer_id=None, role=UserRole.ADMIN)

    expected = CancelOrderResult(
        status="CANCELLED",
        order_number="ORD-20001",
        message="Order ORD-20001 was cancelled successfully."
    )

    with patch("src.tools.order_tools.cancel_order", return_value=expected) as mock_cancel:
        result = cancel_order_tool(db=db, order_id="ORD-20001", user=user, customer_id=1)

    assert result == expected

    mock_cancel.assert_called_once_with(db=db, order_id="ORD-20001", customer_id=1)


def test_cancel_order_tool_returns_not_found_result() -> None:
    db = Mock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    expected = CancelOrderResult(
        status="NOT_FOUND",
        order_number="ORD-99999",
        message="Order ORD-99999 was not found."
    )

    with patch("src.tools.order_tools.cancel_order", return_value=expected) as mock_cancel:
        result = cancel_order_tool(db=db, order_id="ORD-99999", user=user)

    assert result == expected

    mock_cancel.assert_called_once_with(db=db, order_id="ORD-99999", customer_id=1)


def test_cancel_order_tool_customer_cannot_override_customer_context() -> None:
    db = Mock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with pytest.raises(PermissionError):
        cancel_order_tool(db=db, order_id="ORD-20001", user=user, customer_id=2)


def test_cancel_order_tool_support_agent_without_customer_context_is_rejected() -> None:
    db = Mock()

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    with pytest.raises(ValueError, match="Customer ID is required"):
        cancel_order_tool(db=db, order_id="ORD-20001", user=user)
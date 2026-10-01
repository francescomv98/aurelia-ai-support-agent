from unittest.mock import MagicMock
import pytest
from src.auth.models import AuthenticatedUser, UserRole
from src.services.customer_service import CustomerResult
from src.tools.customer_tools import get_customer_tool

def test_customer_can_access_own_customer() -> None:
    db = MagicMock()

    customer_result = CustomerResult(
        status="FOUND",
        customer_code="CUST-001",
        name="Alfa Manufacturing S.p.A.",
        industry="Industrial Manufacturing",
        country="Italy",
        message="Customer CUST-001: Alfa Manufacturing S.p.A."
    )

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with pytest.MonkeyPatch.context() as monkeypatch:
        get_customer_mock = MagicMock(return_value=customer_result)

        monkeypatch.setattr("src.tools.customer_tools.get_customer", get_customer_mock)

        result = get_customer_tool(db=db, user=user)

    assert result.status == "FOUND"
    assert result.customer_code == "CUST-001"
    assert result.name == "Alfa Manufacturing S.p.A."

    get_customer_mock.assert_called_once_with(db=db, customer_id=1)


def test_customer_cannot_override_customer_context() -> None:
    db = MagicMock()

    customer_result = CustomerResult(
        status="FOUND",
        customer_code="CUST-001",
        name="Alfa Manufacturing S.p.A.",
        industry="Industrial Manufacturing",
        country="Italy",
        message="Customer CUST-001: Alfa Manufacturing S.p.A."
    )

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with pytest.MonkeyPatch.context() as monkeypatch:
        get_customer_mock = MagicMock(return_value=customer_result)

        monkeypatch.setattr("src.tools.customer_tools.get_customer", get_customer_mock)

        result = get_customer_tool(db=db, user=user, customer_id=2)

    assert result.status == "FOUND"

    get_customer_mock.assert_called_once_with(db=db, customer_id=1)


def test_customer_without_customer_context_is_rejected() -> None:
    db = MagicMock()

    user = AuthenticatedUser(user_id=1, customer_id=None, role=UserRole.CUSTOMER)

    with pytest.raises(PermissionError):
        get_customer_tool(db=db, user=user)


def test_support_agent_requires_target_customer() -> None:
    db = MagicMock()

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    with pytest.raises(ValueError):
        get_customer_tool(db=db, user=user)


def test_support_agent_can_access_target_customer() -> None:
    db = MagicMock()

    customer_result = CustomerResult(
        status="FOUND",
        customer_code="CUST-001",
        name="Alfa Manufacturing S.p.A.",
        industry="Industrial Manufacturing",
        country="Italy",
        message="Customer CUST-001: Alfa Manufacturing S.p.A."
    )

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    with pytest.MonkeyPatch.context() as monkeypatch:
        get_customer_mock = MagicMock(return_value=customer_result)

        monkeypatch.setattr("src.tools.customer_tools.get_customer", get_customer_mock)

        result = get_customer_tool(db=db, user=user, customer_id=1)

    assert result.status == "FOUND"
    assert result.customer_code == "CUST-001"

    get_customer_mock.assert_called_once_with(db=db, customer_id=1)
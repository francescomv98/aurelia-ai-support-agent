from unittest.mock import MagicMock
import pytest
from src.auth.models import AuthenticatedUser
from src.auth.models import UserRole
from src.services.shipment_service import ShipmentResult
from src.tools.shipment_tools import get_shipment_tool
from src.services.exceptions import AuthorizationError, ValidationError

def test_customer_can_access_own_shipment() -> None:
    db = MagicMock()

    shipment_result = ShipmentResult(
        status="FOUND",
        tracking_number="SHIP-90231",
        carrier="DHL",
        shipment_status="IN_TRANSIT",
        estimated_delivery=None,
        message="Shipment SHIP-90231 is currently IN_TRANSIT."
    )

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.tools.shipment_tools.get_shipment", MagicMock(return_value=shipment_result))

        result = get_shipment_tool(db=db, tracking_number="SHIP-90231", user=user)

    assert result.status == "FOUND"
    assert result.tracking_number == "SHIP-90231"


def test_customer_cannot_override_customer_context() -> None:
    db = MagicMock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    shipment_result = ShipmentResult(
        status="FOUND",
        tracking_number="SHIP-90231",
        carrier="DHL",
        shipment_status="IN_TRANSIT",
        estimated_delivery=None,
        message="Shipment SHIP-90231 is currently IN_TRANSIT."
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        get_shipment_mock = MagicMock(return_value=shipment_result)

        monkeypatch.setattr("src.tools.shipment_tools.get_shipment", get_shipment_mock)

        result = get_shipment_tool(db=db, tracking_number="SHIP-90231", user=user, customer_id=2)

    assert result.status == "FOUND"

    get_shipment_mock.assert_called_once()

    call_kwargs = get_shipment_mock.call_args.kwargs
    assert call_kwargs["customer_id"] == 1


def test_customer_without_customer_context_is_rejected() -> None:
    db = MagicMock()

    user = AuthenticatedUser(user_id=1, customer_id=None, role=UserRole.CUSTOMER)

    with pytest.raises(AuthorizationError):
        get_shipment_tool(db=db, tracking_number="SHIP-90231", user=user)


def test_support_agent_requires_target_customer() -> None:
    db = MagicMock()

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    with pytest.raises(ValidationError):
        get_shipment_tool(db=db, tracking_number="SHIP-90231", user=user)


def test_support_agent_can_access_target_customer_shipment() -> None:
    db = MagicMock()

    shipment_result = ShipmentResult(
        status="FOUND",
        tracking_number="SHIP-90231",
        carrier="DHL",
        shipment_status="IN_TRANSIT",
        estimated_delivery=None,
        message="Shipment SHIP-90231 is currently IN_TRANSIT."
    )

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.tools.shipment_tools.get_shipment", MagicMock(return_value=shipment_result))

        result = get_shipment_tool(db=db, tracking_number="SHIP-90231", user=user, customer_id=1)

    assert result.status == "FOUND"
    assert result.tracking_number == "SHIP-90231"
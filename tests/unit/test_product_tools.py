from unittest.mock import MagicMock
import pytest
from src.auth.models import AuthenticatedUser, UserRole
from src.services.product_service import ProductResult
from src.tools.product_tools import get_product_tool

def test_customer_can_access_product() -> None:
    db = MagicMock()

    product_result = ProductResult(
        status="FOUND",
        product_code="SP-204",
        name="Cooling System Sensor",
        category="SPARE_PART",
        capacity_per_minute=None,
        maintenance_interval_hours=None,
        message="Product SP-204: Cooling System Sensor."
    )

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with pytest.MonkeyPatch.context() as monkeypatch:
        get_product_mock = MagicMock(return_value=product_result)

        monkeypatch.setattr("src.tools.product_tools.get_product", get_product_mock)

        result = get_product_tool(db=db, product_code="SP-204", user=user)

    assert result.status == "FOUND"
    assert result.product_code == "SP-204"
    assert result.name == "Cooling System Sensor"

    get_product_mock.assert_called_once_with(db=db, product_code="SP-204")


def test_product_not_found() -> None:
    db = MagicMock()

    product_result = ProductResult(
        status="NOT_FOUND",
        product_code=None,
        name=None,
        category=None,
        capacity_per_minute=None,
        maintenance_interval_hours=None,
        message="The product UNKNOWN-001 was not found in the system."
    )

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.tools.product_tools.get_product", MagicMock(return_value=product_result))

        result = get_product_tool(db=db, product_code="UNKNOWN-001", user=user)

    assert result.status == "NOT_FOUND"
    assert result.product_code is None
from unittest.mock import MagicMock
from src.services.product_service import get_product

def test_get_product_returns_product() -> None:
    db = MagicMock()

    product = MagicMock()
    product.product_code = "SP-204"
    product.name = "Cooling System Sensor"
    product.category = "SPARE_PART"
    product.capacity_per_minute = None
    product.maintenance_interval_hours = None

    db.scalar.return_value = product

    result = get_product(db=db, product_code="SP-204")

    assert result.status == "FOUND"
    assert result.product_code == "SP-204"
    assert result.name == "Cooling System Sensor"
    assert result.category == "SPARE_PART"
    assert result.capacity_per_minute is None
    assert result.maintenance_interval_hours is None
    assert "SP-204" in result.message


def test_get_product_returns_not_found() -> None:
    db = MagicMock()
    db.scalar.return_value = None

    result = get_product(db=db, product_code="UNKNOWN-001")

    assert result.status == "NOT_FOUND"
    assert result.product_code is None
    assert result.name is None
    assert result.category is None
    assert result.capacity_per_minute is None
    assert result.maintenance_interval_hours is None
    assert "not found" in result.message.lower()
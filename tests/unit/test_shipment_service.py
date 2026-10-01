from datetime import datetime
from unittest.mock import MagicMock
from src.services.shipment_service import get_shipment

def test_get_shipment_returns_shipment() -> None:
    db = MagicMock()

    shipment = MagicMock()
    shipment.tracking_number = "SHIP-90231"
    shipment.carrier = "DHL"
    shipment.status.value = "IN_TRANSIT"
    shipment.estimated_delivery = datetime(2026, 9, 30)

    db.scalar.return_value = shipment

    result = get_shipment(db=db, tracking_number="SHIP-90231", customer_id=1)

    assert result.status == "FOUND"
    assert result.tracking_number == "SHIP-90231"
    assert result.carrier == "DHL"
    assert result.shipment_status == "IN_TRANSIT"
    assert result.estimated_delivery == datetime(2026, 9, 30)
    assert "SHIP-90231" in result.message


def test_get_shipment_returns_not_found() -> None:
    db = MagicMock()
    db.scalar.return_value = None

    result = get_shipment(db=db, tracking_number="SHIP-90231", customer_id=2)

    assert result.status == "NOT_FOUND"
    assert result.tracking_number is None
    assert result.carrier is None
    assert result.shipment_status is None
    assert result.estimated_delivery is None
    assert "not found" in result.message.lower()
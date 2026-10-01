from unittest.mock import MagicMock
from src.services.customer_service import get_customer

def test_get_customer_returns_customer() -> None:
    db = MagicMock()

    customer = MagicMock()
    customer.id = 1
    customer.customer_code = "CUST-001"
    customer.name = "Alfa Manufacturing S.p.A."
    customer.industry = "Industrial Manufacturing"
    customer.country = "Italy"

    db.scalar.return_value = customer

    result = get_customer(db=db, customer_id=1)

    assert result.status == "FOUND"
    assert result.customer_code == "CUST-001"
    assert result.name == "Alfa Manufacturing S.p.A."
    assert result.industry == "Industrial Manufacturing"
    assert result.country == "Italy"
    assert "CUST-001" in result.message


def test_get_customer_returns_not_found() -> None:
    db = MagicMock()
    db.scalar.return_value = None

    result = get_customer(db=db, customer_id=999)

    assert result.status == "NOT_FOUND"
    assert result.customer_code is None
    assert result.name is None
    assert result.industry is None
    assert result.country is None
    assert "not found" in result.message.lower()
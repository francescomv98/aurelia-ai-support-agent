import pytest
from src.database.session import SessionLocal
from src.tools.ticket_tools import get_machine_ticket_tool


@pytest.mark.integration
def test_customer_can_access_own_machine_ticket() -> None:
    db = SessionLocal()

    try:
        result = get_machine_ticket_tool(db=db, machine_serial="AIS2-2025-00142", customer_id=1)

        assert result.status == "FOUND"
        assert result.ticket_number == "TCK-5021"
        assert result.ticket_status == "IN_PROGRESS"

    finally:
        db.close()


@pytest.mark.integration
def test_customer_cannot_access_another_customer_ticket() -> None:
    db = SessionLocal()

    try:
        result = get_machine_ticket_tool(db=db, machine_serial="AIS2-2025-00142", customer_id=2)

        assert result.status == "NOT_FOUND"
        assert result.ticket_number is None

    finally:
        db.close()
import pytest
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.database.session import SessionLocal
from src.tools.ticket_tools import get_machine_ticket_tool

@pytest.mark.integration
def test_customer_can_access_own_machine_ticket() -> None:
    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    db = SessionLocal()

    try:
        result = get_machine_ticket_tool(db=db, machine_serial="AIS2-2025-00142", user=user)

        assert result.status == "FOUND"
        assert result.ticket_number is not None
        assert result.ticket_status is not None
        assert result.category is not None
        assert result.priority is not None

    finally:
        db.close()


@pytest.mark.integration
def test_customer_cannot_access_another_customer_ticket() -> None:
    user = AuthenticatedUser(user_id=1, customer_id=2, role=UserRole.CUSTOMER)

    db = SessionLocal()

    try:
        result = get_machine_ticket_tool(db=db, machine_serial="AIS2-2025-00142", user=user)

        assert result.status == "NOT_FOUND"
        assert result.ticket_number is None

    finally:
        db.close()
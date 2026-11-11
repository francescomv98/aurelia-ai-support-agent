import pytest
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.tools.ticket_tools import get_machine_ticket_tool
from src.services.ticket_service import TicketResult
from src.services.exceptions import AuthorizationError

def test_customer_can_access_own_machine_ticket(monkeypatch) -> None:
    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    def fake_get_machine_ticket(db, machine_serial: str, customer_id: int) -> TicketResult:
        assert machine_serial == "AIS2-2025-00142"
        assert customer_id == 1

        return TicketResult(
            status="FOUND",
            ticket_number="TCK-5021",
            category="TECHNICAL",
            priority="P2",
            ticket_status="IN_PROGRESS",
            subject="AIS-200 E-204 cooling system warning",
            message="Support ticket TCK-5021 exists."
        )

    monkeypatch.setattr("src.tools.ticket_tools.get_machine_ticket", fake_get_machine_ticket)

    result = get_machine_ticket_tool(db=object(), machine_serial="AIS2-2025-00142", user=user)

    assert isinstance(result, TicketResult)
    assert result.status == "FOUND"
    assert result.ticket_number == "TCK-5021"
    assert result.ticket_status == "IN_PROGRESS"


def test_customer_without_customer_context_is_rejected() -> None:
    user = AuthenticatedUser(user_id=1, customer_id=None, role=UserRole.CUSTOMER)

    with pytest.raises(AuthorizationError, match="Customer user has no customer context."):
        get_machine_ticket_tool(db=object(), machine_serial="AIS2-2025-00142", user=user)


@pytest.mark.parametrize("role", [UserRole.SUPPORT_AGENT, UserRole.ADMIN])
def test_staff_user_is_rejected(role: UserRole) -> None:
    user = AuthenticatedUser(user_id=10, customer_id=None, role=role)

    with pytest.raises(AuthorizationError):
        get_machine_ticket_tool(db=object(), machine_serial="AIS2-2025-00142", user=user)

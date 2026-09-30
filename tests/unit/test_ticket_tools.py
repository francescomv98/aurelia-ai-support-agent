from src.services.ticket_service import TicketResult
from src.tools.ticket_tools import get_machine_ticket_tool


def test_get_machine_ticket_tool(monkeypatch) -> None:
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

    result = get_machine_ticket_tool(db=object(), machine_serial="AIS2-2025-00142", customer_id=1)

    assert isinstance(result, TicketResult)
    assert result.status == "FOUND"
    assert result.ticket_number == "TCK-5021"
    assert result.ticket_status == "IN_PROGRESS"
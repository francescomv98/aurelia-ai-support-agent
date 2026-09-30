from src.services.ticket_service import TicketResult

def test_ticket_result_found() -> None:
    result = TicketResult(
        status="FOUND",
        ticket_number="TCK-5021",
        category="TECHNICAL",
        priority="P2",
        ticket_status="IN_PROGRESS",
        subject="AIS-200 E-204 cooling system warning",
        message="Support ticket TCK-5021 exists.",
    )

    assert result.status == "FOUND"
    assert result.ticket_number == "TCK-5021"
    assert result.priority == "P2"
    assert result.ticket_status == "IN_PROGRESS"


def test_ticket_result_not_found() -> None:
    result = TicketResult(status="NOT_FOUND", message="No support ticket was found for this machine.")

    assert result.status == "NOT_FOUND"
    assert result.ticket_number is None
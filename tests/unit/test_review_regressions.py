"""Regression tests for bugs found during code review."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
import openai
import pytest
from src.agent.action_preparation import prepare_action
from src.agent.graph import TICKET_KEYWORD_PATTERN
from src.agent.router import route_request
from src.auth.models import AuthenticatedUser, UserRole
from src.security.rate_limiter import RateLimiter
from src.services.exceptions import LLMError, ValidationError
from src.services.maintenance_service import get_maintenance_history
from src.services.shipment_service import get_shipment
from src.services.support_ticket_service import create_support_ticket, update_support_ticket


def create_state(user_query: str) -> dict:
    return {
        "user_query": user_query,
        "authenticated_user": AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER),
        "route": "tool",
        "retrieved_context": [],
        "rag_available": True,
        "tool_type": None,
        "pending_action": None,
        "tool_result": "",
        "response": ""
    }


def test_get_shipment_handles_plain_string_status_from_database() -> None:
    # String(50) columns return str, not the Enum, so `.value` must not be required.
    db = MagicMock()
    db.scalar.return_value = SimpleNamespace(tracking_number="SHIP-90231", carrier="DHL", status="IN_TRANSIT", estimated_delivery=None)

    result = get_shipment(db=db, tracking_number="SHIP-90231", customer_id=1)

    assert result.shipment_status == "IN_TRANSIT"
    assert "IN_TRANSIT" in result.message


def test_get_maintenance_history_handles_plain_string_type_from_database() -> None:
    db = MagicMock()
    db.scalar.return_value = SimpleNamespace(id=1, serial_number="AIS2-2025-00142")
    db.scalars.return_value.all.return_value = [
        SimpleNamespace(maintenance_type="PREVENTIVE", performed_at=datetime(2026, 1, 15), operating_hours=1500, notes=None)
    ]

    result = get_maintenance_history(db=db, machine_serial="AIS2-2025-00142", customer_id=1)

    assert result.status == "FOUND"
    assert "PREVENTIVE maintenance performed" in result.message


@pytest.mark.parametrize("query", [
    "What is the status of my purchase order ORD-10245?",
    "Has my new order ORD-10245 shipped yet?",
])
def test_read_only_order_questions_do_not_trigger_create_order(query: str) -> None:
    chat_model = MagicMock()

    result = prepare_action(create_state(query), chat_model=chat_model)

    assert result["pending_action"] is None
    chat_model.with_structured_output.assert_not_called()


def test_explicit_purchase_request_still_triggers_create_order() -> None:
    chat_model = MagicMock()
    item = SimpleNamespace(product_code="AIS-200", quantity=1)
    chat_model.with_structured_output.return_value.invoke.return_value = SimpleNamespace(items=[item])

    result = prepare_action(create_state("I want to purchase one AIS-200."), chat_model=chat_model)

    assert result["pending_action"].action_type == "create_order"


@pytest.mark.parametrize("query, expected", [
    ("do i have a ticket for aisx?", True),
    ("show my support tickets", True),
    ("is there an open support case?", True),
    ("in case of error e-204 what should i do?", False),
    ("showcase the machine status", False),
])
def test_ticket_keyword_matching(query: str, expected: bool) -> None:
    assert (TICKET_KEYWORD_PATTERN.search(query) is not None) is expected


def test_create_support_ticket_rejects_invalid_priority() -> None:
    db = MagicMock()

    with pytest.raises(ValidationError, match="Invalid ticket priority"):
        create_support_ticket(db=db, customer_id=1, category="TECHNICAL", priority="HIGH", subject="Error", description="Machine error.")

    db.add.assert_not_called()


def test_update_support_ticket_rejects_invalid_status() -> None:
    db = MagicMock()

    with pytest.raises(ValidationError, match="Invalid ticket status"):
        update_support_ticket(db=db, ticket_number="TCK-5021", customer_id=1, status="DONE")

    db.commit.assert_not_called()


def test_update_support_ticket_normalizes_status() -> None:
    db = MagicMock()
    ticket = SimpleNamespace(ticket_number="TCK-5021", status="OPEN", priority="P2", subject="s", description="d")
    db.scalar.return_value = ticket

    update_support_ticket(db=db, ticket_number="TCK-5021", customer_id=1, status="in progress")

    assert ticket.status == "IN_PROGRESS"


def test_route_request_maps_openai_errors_to_llm_error() -> None:
    chat_model = MagicMock()
    chat_model.with_structured_output.return_value.invoke.side_effect = openai.APIConnectionError(request=MagicMock())

    with pytest.raises(LLMError):
        route_request(create_state("What is the status of order ORD-10245?"), chat_model)


def test_rate_limiter_purges_idle_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1000.0]
    monkeypatch.setattr("src.security.rate_limiter.time.monotonic", lambda: now[0])

    limiter = RateLimiter(max_requests=5, window_seconds=60)

    for index in range(100):
        limiter.is_allowed(f"client-{index}")

    now[0] += 120
    limiter.is_allowed("new-client")

    assert set(limiter._requests) == {"new-client"}

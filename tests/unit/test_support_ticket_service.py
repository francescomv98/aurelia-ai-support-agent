from datetime import datetime
import pytest
from src.services.support_ticket_service import (CreateSupportTicketResult, create_support_ticket, update_support_ticket)
from unittest.mock import MagicMock

class FakeMachine:
    def __init__(self, machine_id=1):
        self.id = machine_id


class FakeSupportTicket:
    def __init__(self, ticket_number="TCK-5021", customer_id=1, status="OPEN", priority="P2", subject="Machine issue", description="The machine reports an error."):
        self.ticket_number = ticket_number
        self.customer_id = customer_id
        self.status = status
        self.priority = priority
        self.subject = subject
        self.description = description


class FakeSession:
    def __init__(self, machine=None, existing_ticket_numbers=None, ticket=None, scalar_exception=None):
        self.machine = machine
        self.existing_ticket_numbers = existing_ticket_numbers or []
        self.ticket = ticket
        self.scalar_exception = scalar_exception
        self.added = []
        self.committed = False
        self.rolled_back = False

    def scalar(self, statement):
        if self.scalar_exception:
            raise self.scalar_exception

        statement_text = str(statement)

        if "machines.id" in statement_text:
            return self.machine

        if "support_tickets.ticket_number" in statement_text:
            return self.ticket

        return None

    def scalars(self, statement):
        return FakeScalarResult(self.existing_ticket_numbers)

    def add(self, entity):
        self.added.append(entity)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


def test_create_support_ticket_success():
    db = FakeSession(
        existing_ticket_numbers=[
            "TCK-5021",
            "TCK-5034",
            "TCK-5041",
            "TCK-5042",
            "TCK-5043"
        ]
    )

    result = create_support_ticket(db=db, customer_id=1, category="TECHNICAL", priority="P2", subject="Cooling system error", description="Machine reports error E-204.")

    assert isinstance(result, CreateSupportTicketResult)
    assert result.status == "CREATED"
    assert result.ticket_number == "TCK-5044"

    assert db.committed is True
    assert db.rolled_back is False
    assert len(db.added) == 1

    ticket = db.added[0]

    assert ticket.ticket_number == "TCK-5044"
    assert ticket.category == "TECHNICAL"
    assert ticket.priority == "P2"
    assert ticket.status == "OPEN"
    assert ticket.subject == "Cooling system error"
    assert ticket.description == "Machine reports error E-204."
    assert ticket.customer_id == 1
    assert ticket.machine_id is None
    assert isinstance(ticket.created_at, datetime)


def test_create_support_ticket_with_machine():
    machine = FakeMachine(machine_id=42)

    db = FakeSession(machine=machine, existing_ticket_numbers=["TCK-5043"])

    result = create_support_ticket(db=db, customer_id=1, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.", machine_id=42)

    assert result.status == "CREATED"
    assert result.ticket_number == "TCK-5044"

    ticket = db.added[0]

    assert ticket.machine_id == 42
    assert ticket.customer_id == 1


def test_create_support_ticket_rejects_machine_of_another_customer():
    db = FakeSession(machine=None)

    result = create_support_ticket(db=db, customer_id=1, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.", machine_id=99)

    assert result.status == "FAILED"
    assert result.ticket_number is None
    assert "machine was not found" in result.message.lower()
    assert db.committed is False


@pytest.mark.parametrize("field", ["category", "priority", "subject", "description"])
def test_create_support_ticket_rejects_empty_required_fields(field):
    db = FakeSession()

    values = {
        "category": "TECHNICAL",
        "priority": "P2",
        "subject": "Test ticket",
        "description": "Test description"
    }

    values[field] = ""

    with pytest.raises(ValueError):
        create_support_ticket(db=db, customer_id=1, **values)


def test_create_support_ticket_rolls_back_on_database_error():
    class FailingSession(FakeSession):
        def commit(self):
            raise RuntimeError("Database error")

    db = FailingSession()

    with pytest.raises(RuntimeError, match="Database error"):
        create_support_ticket(db=db, customer_id=1, category="TECHNICAL", priority="P2", subject="Test ticket", description="Test description")

    assert db.committed is False
    assert db.rolled_back is True


def test_update_support_ticket_status():
    ticket = FakeSupportTicket(status="OPEN")
    db = FakeSession(ticket=ticket)

    result = update_support_ticket(db=db, ticket_number="TCK-5021", customer_id=1, status="IN_PROGRESS")

    assert result.status == "UPDATED"
    assert result.ticket_number == "TCK-5021"
    assert ticket.status == "IN_PROGRESS"
    assert db.committed is True


def test_update_support_ticket_priority():
    ticket = FakeSupportTicket(priority="P2")
    db = FakeSession(ticket=ticket)

    result = update_support_ticket(db=db, ticket_number="TCK-5021", customer_id=1, priority="P1")

    assert result.status == "UPDATED"
    assert ticket.priority == "P1"
    assert db.committed is True


def test_update_support_ticket_multiple_fields():
    ticket = FakeSupportTicket(
        status="OPEN",
        priority="P2",
        subject="Old subject",
        description="Old description"
    )
    db = FakeSession(ticket=ticket)

    result = update_support_ticket(db=db, ticket_number="TCK-5021", customer_id=1, status="IN_PROGRESS", priority="P1", subject="Updated subject", description="Updated description")

    assert result.status == "UPDATED"
    assert ticket.status == "IN_PROGRESS"
    assert ticket.priority == "P1"
    assert ticket.subject == "Updated subject"
    assert ticket.description == "Updated description"
    assert db.committed is True


def test_update_support_ticket_not_found():
    db = FakeSession(ticket=None)

    result = update_support_ticket(db=db, ticket_number="TCK-9999", customer_id=1, status="CLOSED")

    assert result.status == "NOT_FOUND"
    assert result.ticket_number is None
    assert db.committed is False


def test_update_support_ticket_requires_at_least_one_field():
    db = FakeSession(ticket=FakeSupportTicket())

    with pytest.raises(ValueError, match="At least one ticket field"):
        update_support_ticket(db=db, ticket_number="TCK-5021", customer_id=1)


def test_update_support_ticket_rejects_empty_subject():
    db = FakeSession(ticket=FakeSupportTicket())

    with pytest.raises(ValueError, match="Ticket subject cannot be empty"):
        update_support_ticket(db=db, ticket_number="TCK-5021", customer_id=1, subject="   ")


def test_update_support_ticket_rejects_empty_description():
    db = FakeSession(ticket=FakeSupportTicket())

    with pytest.raises(ValueError, match="Ticket description cannot be empty"):
        update_support_ticket(db=db, ticket_number="TCK-5021", customer_id=1, description="   ")


def test_update_support_ticket_rolls_back_on_database_error():
    db = FakeSession(ticket=FakeSupportTicket(), scalar_exception=RuntimeError("Database error"))

    with pytest.raises(RuntimeError, match="Database error"):
        update_support_ticket(db=db, ticket_number="TCK-5021", customer_id=1, status="CLOSED")

    assert db.rolled_back is True
    assert db.committed is False
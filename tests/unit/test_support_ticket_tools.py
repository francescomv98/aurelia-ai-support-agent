from unittest.mock import Mock, patch
import pytest
from src.auth.models import AuthenticatedUser, UserRole
from src.database.models import UserRole
from src.services.support_ticket_service import CreateSupportTicketResult
from src.tools.support_ticket_tools import create_support_ticket_tool, update_support_ticket_tool
from unittest.mock import MagicMock

class FakeSupportTicket:
    def __init__(self, ticket_number="TCK-5021", customer_id=1, status="OPEN", priority="P2", subject="Machine issue", description="The machine reports an error."):
        self.ticket_number = ticket_number
        self.customer_id = customer_id
        self.status = status
        self.priority = priority
        self.subject = subject
        self.description = description


class FakeSession:
    def __init__(self, ticket=None):
        self.ticket = ticket
        self.committed = False
        self.rolled_back = False

    def scalar(self, statement):
        return self.ticket

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_create_support_ticket_tool_customer_uses_own_customer_context():
    db = Mock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    expected = CreateSupportTicketResult(
        status="CREATED",
        ticket_number="TCK-5044",
        message="Support ticket TCK-5044 was created successfully."
    )

    with patch("src.tools.support_ticket_tools.create_support_ticket", return_value=expected) as mock_create:
        result = create_support_ticket_tool(db=db, user=user, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.")

    assert result == expected

    mock_create.assert_called_once_with(db=db, customer_id=1, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.", machine_id=None)


def test_create_support_ticket_tool_customer_cannot_override_customer_context():
    db = Mock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with pytest.raises(PermissionError, match="cannot create tickets for another customer"):
        create_support_ticket_tool(db=db, user=user, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.", customer_id=2)


def test_create_support_ticket_tool_customer_without_context():
    db = Mock()

    user = AuthenticatedUser(user_id=1, customer_id=None, role=UserRole.CUSTOMER)

    with pytest.raises(PermissionError, match="not associated with a customer"):
        create_support_ticket_tool(db=db, user=user, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.")


def test_create_support_ticket_tool_support_agent_requires_customer_id():
    db = Mock()

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    with pytest.raises(ValueError, match="Customer ID is required"):
        create_support_ticket_tool(db=db, user=user, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.")


def test_create_support_ticket_tool_support_agent_can_create_for_customer():
    db = Mock()

    user = AuthenticatedUser(user_id=10, customer_id=None, role=UserRole.SUPPORT_AGENT)

    expected = CreateSupportTicketResult(
        status="CREATED",
        ticket_number="TCK-5044",
        message="Support ticket TCK-5044 was created successfully."
    )

    machine = MagicMock()
    machine.id = 42

    with (patch("src.tools.support_ticket_tools.get_machine_by_serial", return_value=machine) as machine_lookup,
          patch("src.tools.support_ticket_tools.create_support_ticket", return_value=expected) as mock_create):
        result = create_support_ticket_tool(db=db, user=user, customer_id=1, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.", machine_serial="AIS2-2025-00142")

    assert result == expected
    
    machine_lookup.assert_called_once_with(db=db, machine_serial="AIS2-2025-00142", customer_id=1)
    mock_create.assert_called_once_with(db=db, customer_id=1, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.", machine_id=42)


def test_create_support_ticket_tool_admin_can_create_for_customer():
    db = Mock()

    user = AuthenticatedUser(user_id=20, customer_id=None, role=UserRole.ADMIN)

    expected = CreateSupportTicketResult(
        status="CREATED",
        ticket_number="TCK-5044",
        message="Support ticket TCK-5044 was created successfully."
    )

    with patch("src.tools.support_ticket_tools.create_support_ticket", return_value=expected) as mock_create:
        result = create_support_ticket_tool(db=db, user=user, customer_id=1, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.")

    assert result == expected

    mock_create.assert_called_once_with(db=db, customer_id=1, category="TECHNICAL", priority="P2", subject="Machine error", description="Machine reports E-204.", machine_id=None)


def test_customer_can_update_own_ticket():
    db = FakeSession(ticket=FakeSupportTicket())

    user = AuthenticatedUser(user_id=1, username="alfa.support", role=UserRole.CUSTOMER, customer_id=1)

    result = update_support_ticket_tool(db=db, user=user, ticket_number="TCK-5021", status="IN_PROGRESS")

    assert result.status == "UPDATED"
    assert result.ticket_number == "TCK-5021"


def test_customer_cannot_update_ticket_for_another_customer():
    db = FakeSession(ticket=FakeSupportTicket())

    user = AuthenticatedUser(user_id=1, username="alfa.support", role=UserRole.CUSTOMER, customer_id=1)

    with pytest.raises(PermissionError, match="cannot update tickets for another customer"):
        update_support_ticket_tool(db=db, user=user, ticket_number="TCK-5021", status="CLOSED", customer_id=2)


def test_customer_without_customer_context_cannot_update_ticket():
    db = FakeSession(ticket=FakeSupportTicket())

    user = AuthenticatedUser(user_id=1, username="customer", role=UserRole.CUSTOMER, customer_id=None)

    with pytest.raises(PermissionError, match="not associated with a customer"):
        update_support_ticket_tool(db=db, user=user, ticket_number="TCK-5021", status="CLOSED")


def test_support_agent_requires_customer_id():
    db = FakeSession(ticket=FakeSupportTicket())

    user = AuthenticatedUser(user_id=2, username="mario.rossi", role=UserRole.SUPPORT_AGENT, customer_id=None)

    with pytest.raises(ValueError, match="Customer ID is required for internal users"):
        update_support_ticket_tool(db=db, user=user, ticket_number="TCK-5021", status="CLOSED")


def test_support_agent_can_update_customer_ticket():
    db = FakeSession(ticket=FakeSupportTicket())

    user = AuthenticatedUser(user_id=2, username="mario.rossi", role=UserRole.SUPPORT_AGENT, customer_id=None)

    result = update_support_ticket_tool(db=db, user=user, ticket_number="TCK-5021", status="IN_PROGRESS", customer_id=1)

    assert result.status == "UPDATED"
    assert result.ticket_number == "TCK-5021"


def test_admin_can_update_customer_ticket():
    db = FakeSession(ticket=FakeSupportTicket())

    user = AuthenticatedUser(user_id=3, username="admin.system", role=UserRole.ADMIN, customer_id=None)

    result = update_support_ticket_tool(db=db, user=user, ticket_number="TCK-5021", priority="P1", customer_id=1)

    assert result.status == "UPDATED"
    assert result.ticket_number == "TCK-5021"


def test_create_support_ticket_tool_customer_uses_machine_serial() -> None:
    db = MagicMock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    machine = MagicMock()
    machine.id = 42

    db_machine_lookup = MagicMock(return_value=machine)

    expected = CreateSupportTicketResult(
        status="CREATED",
        ticket_number="TCK-5044",
        message="Support ticket TCK-5044 was created successfully."
    )

    create_ticket = MagicMock(return_value=expected)

    with (patch("src.tools.support_ticket_tools.get_machine_by_serial", db_machine_lookup), patch("src.tools.support_ticket_tools.create_support_ticket", create_ticket)):
        result = create_support_ticket_tool(db=db, user=user, category="TECHNICAL", priority="P2", subject="Cooling temperature too high", description="The cooling system temperature is above the expected threshold.", machine_serial="AIS2-2025-00142")

    assert result == expected

    db_machine_lookup.assert_called_once_with(db=db, machine_serial="AIS2-2025-00142", customer_id=1)

    create_ticket.assert_called_once_with(db=db, customer_id=1, category="TECHNICAL", priority="P2", subject="Cooling temperature too high", description="The cooling system temperature is above the expected threshold.", machine_id=42)


def test_create_support_ticket_tool_rejects_machine_from_another_customer() -> None:
    db = MagicMock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with patch("src.tools.support_ticket_tools.get_machine_by_serial", return_value=None) as machine_lookup:
        result = create_support_ticket_tool(db=db, user=user, category="TECHNICAL", priority="P2", subject="Machine issue", description="Machine is not operating correctly.", machine_serial="AIS2-2025-99999")

    assert result.status == "FAILED"
    assert result.ticket_number is None
    assert result.message == "The specified machine was not found for the customer."

    machine_lookup.assert_called_once_with(db=db, machine_serial="AIS2-2025-99999", customer_id=1)


def test_create_support_ticket_tool_without_machine() -> None:
    db = MagicMock()

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    expected = CreateSupportTicketResult(
        status="CREATED",
        ticket_number="TCK-5044",
        message="Support ticket TCK-5044 was created successfully."
    )

    with patch("src.tools.support_ticket_tools.create_support_ticket", return_value=expected) as create_ticket:
        result = create_support_ticket_tool(db=db, user=user, category="ORDER", priority="P3", subject="Order question", description="I need information about my order.")

    assert result == expected

    create_ticket.assert_called_once_with(db=db, customer_id=1, category="ORDER", priority="P3", subject="Order question", description="I need information about my order.", machine_id=None)
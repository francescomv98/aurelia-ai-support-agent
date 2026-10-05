from langchain_core.documents import Document
from src.agent.graph import determine_tool_type, execute_tool
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.services.machine_service import MachineResult
from src.services.ticket_service import TicketResult
from src.services.shipment_service import ShipmentResult
import pytest
from unittest.mock import MagicMock, patch
from src.agent.graph import build_agent_graph
from src.agent.graph import human_approval
from langgraph.checkpoint.memory import InMemorySaver
from src.services.exceptions import AuthorizationError, ValidationError

def create_customer_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)


def test_execute_tool_returns_order_result(monkeypatch) -> None:
    user = create_customer_user()

    def fake_get_order_status_tool(db, order_id: str, user: AuthenticatedUser) -> str:
        assert order_id == "ORD-10245"
        assert user.user_id == 1
        assert user.customer_id == 1
        assert user.role == UserRole.CUSTOMER

        return "Order ORD-10245 is SHIPPED."

    monkeypatch.setattr("src.agent.graph.get_order_status_tool", fake_get_order_status_tool)

    state = {
        "user_query": "What is the status of order ORD-10245?",
        "authenticated_user": user,
        "route": "tool",
        "tool_type": "order",
        "retrieved_context": [],
        "tool_result": "",
        "response": ""
    }

    result = execute_tool(state=state, db=object(), rag_service=object())

    assert result["tool_result"] == "Order ORD-10245 is SHIPPED."


def test_execute_tool_requires_customer_context() -> None:
    user = AuthenticatedUser(user_id=1, customer_id=None, role=UserRole.CUSTOMER)

    state = {
        "user_query": "What is the status of order ORD-10245?",
        "authenticated_user": user,
        "route": "tool",
        "tool_type": "order",
        "retrieved_context": [],
        "tool_result": "",
        "response": ""
    }

    with pytest.raises(AuthorizationError, match="Customer user has no customer context."):
        execute_tool(state=state, db=object(), rag_service=object())


def test_execute_tool_handles_missing_order_id() -> None:
    user = create_customer_user()

    state = {
        "user_query": "Can you check my order?",
        "authenticated_user": user,
        "route": "tool",
        "tool_type": "order",
        "retrieved_context": [],
        "tool_result": "",
        "response": ""
    }

    result = execute_tool(state=state, db=object(), rag_service=object())

    assert result["tool_result"] == "I could not identify an order number."


def test_determine_tool_type_order() -> None:
    state = {
        "user_query": "What is the status of ORD-10245?",
        "authenticated_user": create_customer_user(),
        "route": "tool",
        "tool_type": None,
        "retrieved_context": [],
        "tool_result": "",
        "response": ""
    }

    result = determine_tool_type(state)

    assert result["tool_type"] == "order"


def test_determine_tool_type_machine() -> None:
    state = {
        "user_query": (
            "When does AIS2-2025-00142 need maintenance?"
        ),
        "authenticated_user": create_customer_user(),
        "route": "hybrid",
        "tool_type": None,
        "retrieved_context": [],
        "tool_result": "",
        "response": ""
    }

    result = determine_tool_type(state)

    assert result["tool_type"] == "machine"


def test_determine_tool_type_unknown() -> None:
    state = {
        "user_query": "I need help with something.",
        "authenticated_user": create_customer_user(),
        "route": "tool",
        "tool_type": None,
        "retrieved_context": [],
        "tool_result": "",
        "response": ""
    }

    result = determine_tool_type(state)

    assert result["tool_type"] is None


def test_execute_tool_calculates_machine_maintenance(monkeypatch) -> None:
    user = create_customer_user()

    def fake_get_machine_tool(db, machine_serial: str, user: AuthenticatedUser) -> MachineResult:
        assert machine_serial == "AIS2-2025-00142"
        assert user.user_id == 1
        assert user.customer_id == 1
        assert user.role == UserRole.CUSTOMER

        return MachineResult(
            status="FOUND",
            machine_serial="AIS2-2025-00142",
            model="AIS-200",
            operating_hours=1734,
            message=(
                "Machine AIS2-2025-00142 is an AIS-200 "
                "with 1734 operating hours."
            )
        )

    monkeypatch.setattr("src.agent.graph.get_machine_tool", fake_get_machine_tool)

    class FakeRAGService:
        def extract_maintenance_interval(self, documents, model: str) -> int | None:
            assert model == "AIS-200"
            assert len(documents) == 1

            return 2000

    state = {
        "user_query": (
            "When does machine AIS2-2025-00142 "
            "need maintenance?"
        ),
        "authenticated_user": user,
        "route": "hybrid",
        "tool_type": "machine",
        "retrieved_context": [
            Document(
                page_content=(
                    "AIS-200 preventive maintenance "
                    "every 2,000 operating hours."
                ),
                metadata={}
            )
        ],
        "tool_result": "",
        "response": ""
    }

    result = execute_tool(state=state, db=object(), rag_service=FakeRAGService())

    assert "1734 operating hours" in result["tool_result"]
    assert "266 hours remain" in result["tool_result"]


def test_execute_tool_finds_existing_support_ticket(monkeypatch) -> None:
    user = create_customer_user()

    state = {
        "user_query": (
            "E-204 occurred on AIS2-2025-00142. "
            "Do I already have a support ticket?"
        ),
        "authenticated_user": user,
        "route": "hybrid",
        "retrieved_context": [],
        "tool_type": "machine",
        "tool_result": "",
        "response": ""
    }

    machine_result = MachineResult(
        status="FOUND",
        machine_serial="AIS2-2025-00142",
        model="AIS-200",
        operating_hours=1734,
        message=(
            "Machine AIS2-2025-00142 is an AIS-200 "
            "with 1734 operating hours."
        )
    )

    ticket_result = TicketResult(
        status="FOUND",
        ticket_number="TCK-5021",
        category="TECHNICAL",
        priority="P2",
        ticket_status="IN_PROGRESS",
        subject="AIS-200 E-204 cooling system warning",
        message=(
            "Support ticket TCK-5021 exists for "
            "machine AIS2-2025-00142. "
            "Status: IN_PROGRESS. "
            "Priority: P2. "
            "Subject: AIS-200 E-204 cooling system warning."
        )
    )

    def fake_get_machine_tool(db, machine_serial: str, user: AuthenticatedUser) -> MachineResult:
        assert machine_serial == "AIS2-2025-00142"
        assert user.user_id == 1
        assert user.customer_id == 1

        return machine_result

    def fake_get_machine_ticket_tool(db, machine_serial: str, user: AuthenticatedUser) -> TicketResult:
        assert machine_serial == "AIS2-2025-00142"
        assert user.user_id == 1
        assert user.customer_id == 1

        return ticket_result

    monkeypatch.setattr("src.agent.graph.get_machine_tool", fake_get_machine_tool)

    monkeypatch.setattr("src.agent.graph.get_machine_ticket_tool", fake_get_machine_ticket_tool)

    result = execute_tool(state, db=object(), rag_service=object())

    assert "TCK-5021" in result["tool_result"]
    assert "IN_PROGRESS" in result["tool_result"]
    assert "P2" in result["tool_result"]


def test_determine_shipment_tool_type() -> None:
    state = {
        "user_query": "Where is shipment SHIP-90231?",
        "authenticated_user": AuthenticatedUser(
            user_id=1,
            customer_id=1,
            role=UserRole.CUSTOMER
        ),
        "route": "tool",
        "retrieved_context": [],
        "tool_type": None,
        "tool_result": "",
        "response": ""
    }

    result = determine_tool_type(state)

    assert result["tool_type"] == "shipment"


def test_execute_shipment_tool() -> None:
    db = MagicMock()

    shipment_result = ShipmentResult(
        status="FOUND",
        tracking_number="SHIP-90231",
        carrier="DHL",
        shipment_status="IN_TRANSIT",
        estimated_delivery=None,
        message="Shipment SHIP-90231 is currently IN_TRANSIT. Carrier: DHL."
    )

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    state = {
        "user_query": "Where is shipment SHIP-90231?",
        "authenticated_user": user,
        "route": "tool",
        "retrieved_context": [],
        "tool_type": "shipment",
        "tool_result": "",
        "response": ""
    }

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.agent.graph.get_shipment_tool", MagicMock(return_value=shipment_result))

        result = execute_tool(state=state, db=db, rag_service=MagicMock())

    assert "SHIP-90231" in result["tool_result"]
    assert "DHL" in result["tool_result"]
    assert "IN_TRANSIT" in result["tool_result"]


def test_determine_product_tool():
    state = {
        "user_query": "What is the capacity of the AIS-200?",
        "authenticated_user": ...,
        "route": "tool",
        "retrieved_context": [],
        "tool_type": None,
        "tool_result": "",
        "response": ""
    }

    result = determine_tool_type(state)

    assert result["tool_type"] == "product"


def test_determine_customer_tool():
    state = {
        "user_query": "Show me information about customer CUST-001.",
        "authenticated_user": ...,
        "route": "tool",
        "retrieved_context": [],
        "tool_type": None,
        "tool_result": "",
        "response": ""
    }

    result = determine_tool_type(state)

    assert result["tool_type"] == "customer"


def test_build_agent_graph_with_checkpointer():
    chat_model = MagicMock()
    rag_service = MagicMock()
    db = MagicMock()
    checkpointer = InMemorySaver()

    graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

    assert graph is not None


def test_human_approval_requires_pending_action():
    state = {
        "user_query": "Hello",
        "authenticated_user": MagicMock(),
        "route": "tool",
        "retrieved_context": [],
        "tool_type": "order",
        "pending_action": None,
        "tool_result": "",
        "response": ""
    }

    with pytest.raises(ValueError, match="No pending action"):
        human_approval(state)


def test_write_action_approved_reaches_execute_write_tool():
    chat_model = MagicMock()

    route_response = MagicMock()
    route_response.route = "tool"

    chat_model.with_structured_output.return_value.invoke.side_effect = [ route_response ]

    rag_service = MagicMock()
    checkpointer = InMemorySaver()
    db = MagicMock()

    with patch("src.agent.graph.request_human_approval", return_value="APPROVED"), patch(
        "src.agent.graph.execute_write_tool",
        return_value={
            "user_query": "Create an order for 2 AIS-200 machines.",
            "authenticated_user": MagicMock(),
            "route": "tool",
            "retrieved_context": [],
            "tool_type": "order",
            "pending_action": MagicMock(),
            "tool_result": "Order created successfully.",
            "response": ""
        }) as mock_execute_write:

        graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)
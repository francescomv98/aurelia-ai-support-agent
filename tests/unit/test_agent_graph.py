from langchain_core.documents import Document
from src.agent.graph import determine_tool_type, execute_tool
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.rag.rag_service import RAGService
from src.services.machine_service import MachineResult
from src.services.ticket_service import TicketResult
from src.services.shipment_service import ShipmentResult
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agent.graph import build_agent_graph, human_approval, generate_response
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from src.services.exceptions import AuthorizationError, LLMError, DatabaseError
from src.agent.action_preparation import CreateOrderAction, OrderItem
from src.agent.state import PendingAction
import openai

def create_customer_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)


@pytest.mark.anyio
async def test_execute_tool_returns_order_result(monkeypatch) -> None:
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
        "rag_available": True,
        "tool_type": "order",
        "retrieved_context": [],
        "tool_result": "",
        "response": ""
    }

    result = await execute_tool(state=state, db=object(), rag_service=object())

    assert result["tool_result"] == "Order ORD-10245 is SHIPPED."


@pytest.mark.anyio
async def test_execute_tool_requires_customer_context() -> None:
    user = AuthenticatedUser(user_id=1, customer_id=None, role=UserRole.CUSTOMER)

    state = {
        "user_query": "What is the status of order ORD-10245?",
        "authenticated_user": user,
        "route": "tool",
        "rag_available": True,
        "tool_type": "order",
        "retrieved_context": [],
        "tool_result": "",
        "response": ""
    }

    with pytest.raises(AuthorizationError):
        await execute_tool(state=state, db=MagicMock(), rag_service=MagicMock())


@pytest.mark.anyio
async def test_execute_tool_handles_missing_order_id() -> None:
    user = create_customer_user()

    state = {
        "user_query": "Can you check my order?",
        "authenticated_user": user,
        "route": "tool",
        "rag_available": True,
        "tool_type": "order",
        "retrieved_context": [],
        "tool_result": "",
        "response": ""
    }

    result = await execute_tool(state=state, db=object(), rag_service=object())

    assert result["tool_result"] == "I could not identify an order number."


def test_determine_tool_type_order() -> None:
    state = {
        "user_query": "What is the status of ORD-10245?",
        "authenticated_user": create_customer_user(),
        "route": "tool",
        "rag_available": True,
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
        "rag_available": True,
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
        "rag_available": True,
        "tool_type": None,
        "retrieved_context": [],
        "tool_result": "",
        "response": ""
    }

    result = determine_tool_type(state)

    assert result["tool_type"] is None


@pytest.mark.anyio
async def test_execute_tool_calculates_machine_maintenance(monkeypatch) -> None:
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
        "rag_available": True,
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

    result = await execute_tool(state=state, db=object(), rag_service=FakeRAGService())

    assert "1734 operating hours" in result["tool_result"]
    assert "266 hours remain" in result["tool_result"]


@pytest.mark.anyio
async def test_execute_tool_finds_existing_support_ticket(monkeypatch) -> None:
    user = create_customer_user()

    state = {
        "user_query": (
            "E-204 occurred on AIS2-2025-00142. "
            "Do I already have a support ticket?"
        ),
        "authenticated_user": user,
        "route": "hybrid",
        "retrieved_context": [],
        "rag_available": True,
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

    result = await execute_tool(state, db=object(), rag_service=object())

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
        "rag_available": True,
        "tool_type": None,
        "tool_result": "",
        "response": ""
    }

    result = determine_tool_type(state)

    assert result["tool_type"] == "shipment"


@pytest.mark.anyio
async def test_execute_shipment_tool() -> None:
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
        "rag_available": True,
        "tool_type": "shipment",
        "tool_result": "",
        "response": ""
    }

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.agent.graph.get_shipment_tool", MagicMock(return_value=shipment_result))

        result = await execute_tool(state=state, db=db, rag_service=MagicMock())

    assert "SHIP-90231" in result["tool_result"]
    assert "DHL" in result["tool_result"]
    assert "IN_TRANSIT" in result["tool_result"]


def test_determine_product_tool():
    state = {
        "user_query": "What is the capacity of the AIS-200?",
        "authenticated_user": ...,
        "route": "tool",
        "retrieved_context": [],
        "rag_available": True,
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
        "rag_available": True,
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
        "authenticated_user": create_customer_user(),
        "route": "tool",
        "retrieved_context": [],
        "rag_available": True,
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

    action_response = CreateOrderAction(items=[OrderItem(product_code="PROD-200", quantity=2)])

    chat_model.with_structured_output.return_value.invoke.side_effect = [ route_response, action_response ]
    chat_model.invoke.return_value.content = "Order created successfully."

    rag_service = MagicMock()
    checkpointer = InMemorySaver()
    db = MagicMock()

    pending_action = PendingAction(
        action_type="create_order",
        description="Create an order for 2 AIS-200 machines.",
        parameters={
            "items": [
                {
                    "product_code": "PROD-200",
                    "quantity": 2
                }
            ]
        }
    )

    execute_write_result = {
        "user_query": "Create an order for 2 AIS-200 machines.",
        "authenticated_user": create_customer_user(),
        "route": "tool",
        "retrieved_context": [],
        "rag_available": True,
        "tool_type": "order",
        "pending_action": pending_action,
        "tool_result": "Order created successfully.",
        "response": ""
    }

    with patch("src.agent.graph.request_human_approval", return_value="APPROVED"), patch("src.agent.graph.execute_write_tool", return_value=execute_write_result) as mock_execute_write:

        graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

        initial_state = {
            "user_query": "Create an order for 2 AIS-200 machines.",
            "authenticated_user": create_customer_user(),
            "route": "rag",
            "retrieved_context": [],
            "rag_available": True,
            "tool_type": None,
            "pending_action": None,
            "tool_result": "",
            "response": ""
        }

        config = { "configurable": { "thread_id": "test-write-action-approved" }}

        result = graph.invoke(initial_state, config=config)

    mock_execute_write.assert_called_once()
    assert result["tool_result"] == "Order created successfully."


def test_generate_response_maps_llm_timeout_to_llm_error() -> None:
    chat_model = MagicMock(spec=ChatOpenAI)
    rag_service = MagicMock(spec=RAGService)

    chat_model.invoke.side_effect = openai.APITimeoutError(request=MagicMock())

    state = {
        "user_query": "What is the warranty period?",
        "authenticated_user":  create_customer_user(),
        "route": "rag",
        "retrieved_context": [],
        "rag_available": True,
        "tool_type": None,
        "pending_action": None,
        "tool_result": "",
        "response": ""
    }

    with pytest.raises(LLMError, match="The AI service timed out."):
        generate_response(state=state, chat_model=chat_model, rag_service=rag_service)


@pytest.mark.anyio
async def test_rag_only_request_degrades_when_rag_is_unavailable():
    chat_model = MagicMock(spec=ChatOpenAI)
    rag_service = MagicMock(spec=RAGService)
    rag_service.retrieve_context.side_effect = DatabaseError("Vector store operation failed.")

    checkpointer = InMemorySaver()
    db = MagicMock()

    with patch("src.agent.graph.route_request") as mock_route:
        mock_route.return_value = {
            "user_query": "What is the warranty period?",
            "authenticated_user": create_customer_user(),
            "route": "rag",
            "retrieved_context": [],
            "rag_available": True,
            "tool_type": None,
            "pending_action": None,
            "tool_result": "",
            "response": ""
        }

        graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

        initial_state = {
            "user_query": "What is the warranty period?",
            "authenticated_user": create_customer_user(),
            "route": "rag",
            "retrieved_context": [],
            "rag_available": True,
            "tool_type": None,
            "pending_action": None,
            "tool_result": "",
            "response": ""
        }

        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test-rag-degradation"}})

    assert result["rag_available"] is False
    assert result["retrieved_context"] == []
    assert result["response"] == "I'm sorry, but the documentation service is currently unavailable. Please try again later."
    chat_model.invoke.assert_not_called()


def test_rag_only_request_returns_fallback_when_rag_is_unavailable():
    chat_model = MagicMock(spec=ChatOpenAI)
    rag_service = MagicMock(spec=RAGService)
    rag_service.retrieve_context.side_effect = DatabaseError("Vector store operation failed.")

    checkpointer = InMemorySaver()
    db = MagicMock()

    route_response = MagicMock()
    route_response.route = "rag"

    chat_model.with_structured_output.return_value.invoke.return_value = route_response

    graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

    initial_state = {
        "user_query": "What is the warranty period?",
        "authenticated_user": create_customer_user(),
        "route": "rag",
        "retrieved_context": [],
        "rag_available": True,
        "tool_type": None,
        "pending_action": None,
        "tool_result": "",
        "response": ""
    }

    result = graph.invoke(initial_state, config={"configurable": {"thread_id": "test-rag-only-degradation"}})

    assert result["route"] == "rag"
    assert result["rag_available"] is False
    assert result["retrieved_context"] == []
    assert result["response"] == "I'm sorry, but the documentation service is currently unavailable. Please try again later."

    rag_service.retrieve_context.assert_called_once_with("What is the warranty period?")
    chat_model.invoke.assert_not_called()


@pytest.mark.anyio
async def test_hybrid_request_executes_tool_when_rag_is_unavailable():
    chat_model = MagicMock(spec=ChatOpenAI)
    rag_service = MagicMock(spec=RAGService)
    rag_service.retrieve_context.side_effect = DatabaseError("Vector store operation failed.")
    rag_service.extract_maintenance_interval.return_value = None

    checkpointer = InMemorySaver()
    db = MagicMock()

    route_response = MagicMock()
    route_response.route = "hybrid"

    chat_model.with_structured_output.return_value.invoke.return_value = route_response
    chat_model.invoke.return_value.content = "Maintenance information is currently unavailable."

    machine_result = MachineResult(
        status="FOUND",
        message=("Machine AIS2-2025-00142 is an AIS-200 machine with 1734 operating hours."),
        machine_serial="AIS2-2025-00142",
        model="AIS-200",
        operating_hours=1734
    )

    with patch("src.agent.graph.get_machine_tool", return_value=machine_result) as mock_machine_tool:
        graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

        initial_state = {
            "user_query": "When does machine AIS2-2025-00142 need maintenance?",
            "authenticated_user": create_customer_user(),
            "route": "rag",
            "retrieved_context": [],
            "rag_available": True,
            "tool_type": None,
            "pending_action": None,
            "tool_result": "",
            "response": ""
        }

        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "test-hybrid-rag-degradation"}})

    assert result["route"] == "hybrid"
    assert result["rag_available"] is False
    assert result["retrieved_context"] == []

    mock_machine_tool.assert_called_once_with(db=db, machine_serial="AIS2-2025-00142", user=initial_state["authenticated_user"])

    assert "Machine AIS2-2025-00142" in result["tool_result"]
    assert "maintenance interval could not be determined" in result["tool_result"]

    chat_model.invoke.assert_called_once()


@pytest.mark.anyio
async def test_execute_tool_uses_mcp_for_order_status() -> None:
    state = {
        "user_query": "What is the status of order ORD-10241?",
        "authenticated_user": AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER),
        "route": "tool",
        "retrieved_context": [],
        "rag_available": True,
        "tool_type": "order",
        "pending_action": None,
        "tool_result": "",
        "response": ""
    }
    
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("src.agent.graph.create_mcp_client", return_value=mock_client), patch("src.agent.graph.call_mcp_tool", new=AsyncMock(return_value="Order ORD-10241 is DELIVERED.")) as mock_call_mcp_tool:
        result = await execute_tool(state=state, db=MagicMock(), rag_service=MagicMock())

    assert result["tool_result"] == "Order ORD-10241 is DELIVERED."

    mock_call_mcp_tool.assert_awaited_once_with(client=mock_client, tool_name="get_order_status_tool",
        arguments={
            "order_id": "ORD-10241",
            "customer_id": 1
        }
    )
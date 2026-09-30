from langchain_core.documents import Document
from src.agent.graph import execute_tool, determine_tool_type
from src.services.machine_service import MachineResult
from src.services.ticket_service import TicketResult

def test_execute_tool_returns_order_result(monkeypatch) -> None:
    def fake_get_order_status_tool(db, order_id: str, customer_id: int) -> str:
        assert order_id == "ORD-10245"
        assert customer_id == 1

        return "Order ORD-10245 is SHIPPED."

    monkeypatch.setattr("src.agent.graph.get_order_status_tool", fake_get_order_status_tool)

    state = {
        "user_query": "What is the status of order ORD-10245?",
        "customer_id": 1,
        "route": "tool",
        "tool_type": "order",
        "retrieved_context": "",
        "tool_result": "",
        "response": ""
    }

    result = execute_tool(state=state, db=object(), rag_service = object())

    assert result["tool_result"] == "Order ORD-10245 is SHIPPED."


def test_execute_tool_requires_customer_context() -> None:
    state = {
        "user_query": "What is the status of order ORD-10245?",
        "customer_id": None,
        "route": "tool",
        "tool_type": "order",
        "retrieved_context": "",
        "tool_result": "",
        "response": ""
    }

    result = execute_tool(state=state, db=object(), rag_service = object())

    assert (result["tool_result"] == "Customer context is required to access enterprise information.")


def test_execute_tool_handles_missing_order_id() -> None:
    state = {
        "user_query": "Can you check my order?",
        "customer_id": 1,
        "route": "tool",
        "tool_type": "order",
        "retrieved_context": "",
        "tool_result": "",
        "response": ""
    }

    result = execute_tool(state=state, db=object(), rag_service = object())

    assert (result["tool_result"] == "I could not identify an order number.")


def test_determine_tool_type_order() -> None:
    state = {
        "user_query": "What is the status of ORD-10245?",
        "customer_id": 1,
        "route": "tool",
        "tool_type": None,
        "retrieved_context": "",
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
        "customer_id": 1,
        "route": "hybrid",
        "tool_type": None,
        "retrieved_context": "",
        "tool_result": "",
        "response": ""
    }

    result = determine_tool_type(state)

    assert result["tool_type"] == "machine"


def test_determine_tool_type_unknown() -> None:
    state = {
        "user_query": "I need help with something.",
        "customer_id": 1,
        "route": "tool",
        "tool_type": None,
        "retrieved_context": "",
        "tool_result": "",
        "response": ""
    }

    result = determine_tool_type(state)

    assert result["tool_type"] is None

def test_execute_tool_calculates_machine_maintenance(
    monkeypatch,
) -> None:
    def fake_get_machine_tool(
        db,
        machine_serial: str,
        customer_id: int,
    ) -> MachineResult:
        assert machine_serial == "AIS2-2025-00142"
        assert customer_id == 1

        return MachineResult(
            status="FOUND",
            machine_serial="AIS2-2025-00142",
            model="AIS-200",
            operating_hours=1734,
            message=(
                "Machine AIS2-2025-00142 is an AIS-200 "
                "with 1734 operating hours."
            ),
        )

    monkeypatch.setattr(
        "src.agent.graph.get_machine_tool",
        fake_get_machine_tool,
    )

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
        "customer_id": 1,
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
    state = {
        "user_query": (
            "E-204 occurred on AIS2-2025-00142. "
            "Do I already have a support ticket?"
        ),
        "customer_id": 1,
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

    monkeypatch.setattr("src.agent.graph.get_machine_tool", lambda db, machine_serial, customer_id: machine_result)
    monkeypatch.setattr("src.agent.graph.get_machine_ticket_tool", lambda db, machine_serial, customer_id: ticket_result)

    result = execute_tool(state, db=object(), rag_service=object())

    assert "TCK-5021" in result["tool_result"]
    assert "IN_PROGRESS" in result["tool_result"]
    assert "P2" in result["tool_result"]
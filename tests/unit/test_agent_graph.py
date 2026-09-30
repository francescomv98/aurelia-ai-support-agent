from src.agent.graph import execute_tool, determine_tool_type

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

    result = execute_tool(state=state, db=object())

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

    result = execute_tool(state=state, db=object())

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

    result = execute_tool(state=state, db=object())

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
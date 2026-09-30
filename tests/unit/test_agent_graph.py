from src.agent.graph import execute_tool

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
        "retrieved_context": "",
        "tool_result": "",
        "response": ""
    }

    result = execute_tool(state=state, db=object())

    assert (result["tool_result"] == "Customer context is required to access order information.")


def test_execute_tool_handles_missing_order_id() -> None:
    state = {
        "user_query": "Can you check my order?",
        "customer_id": 1,
        "route": "tool",
        "retrieved_context": "",
        "tool_result": "",
        "response": ""
    }

    result = execute_tool(state=state, db=object())

    assert (result["tool_result"] == "I could not identify an order number in the request.")
from src.agent.router import route_request

class FakeStructuredModel:
    """Fake structured model for router tests."""

    def __init__(self, route: str) -> None:
        self.route = route

    def invoke(self, prompt: str):
        class FakeDecision:
            pass

        decision = FakeDecision()
        decision.route = self.route

        return decision


class FakeChatModel:
    """Fake chat model supporting structured output."""

    def __init__(self, route: str) -> None:
        self.route = route

    def with_structured_output(self, schema):
        return FakeStructuredModel(self.route)


def test_route_rag_request() -> None:
    state = {
        "user_query": "What is the maximum speed of AIS-200?",
        "route": "rag",
        "retrieved_context": "",
        "response": ""
    }

    result = route_request(state, FakeChatModel("rag"))

    assert result["route"] == "rag"


def test_route_tool_request() -> None:
    state = {
        "user_query": "What is the status of order ORD-10245?",
        "route": "rag",
        "retrieved_context": "",
        "response": ""
    }

    result = route_request(state, FakeChatModel("tool"))

    assert result["route"] == "tool"


def test_route_hybrid_request() -> None:
    state = {
        "user_query": "Does my machine need maintenance?",
        "route": "rag",
        "retrieved_context": "",
        "response": ""
    }

    result = route_request(state, FakeChatModel("hybrid"))

    assert result["route"] == "hybrid"
from unittest.mock import MagicMock
from src.agent.graph import build_agent_graph
from src.agent.checkpointer import create_checkpointer
from src.auth.models import AuthenticatedUser, UserRole
import pytest

@pytest.mark.integration
def test_agent_graph_persists_checkpoint():
    chat_model = MagicMock()

    route_response = MagicMock()
    route_response.route = "rag"

    chat_model.with_structured_output.return_value.invoke.return_value = route_response

    response = MagicMock()
    response.content = "Test response"

    chat_model.invoke.return_value = response

    rag_service = MagicMock()
    rag_service.retrieve_context.return_value = []

    db = MagicMock()

    checkpointer = create_checkpointer()

    agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    initial_state = {
        "user_query": "Hello",
        "authenticated_user": user,
        "route": "rag",
        "retrieved_context": [],
        "rag_available": True,
        "tool_type": None,
        "pending_action": None,
        "tool_result": "",
        "response": ""
    }

    config = { "configurable": { "thread_id": "integration-test-thread" } }

    result = agent_graph.invoke(initial_state, config=config)

    assert result["response"] == "Test response"

    checkpoint = agent_graph.get_state(config)

    assert checkpoint is not None
    assert checkpoint.values["user_query"] == "Hello"
    assert checkpoint.values["response"] == "Test response"
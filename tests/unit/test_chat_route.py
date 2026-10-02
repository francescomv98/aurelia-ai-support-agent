from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from src.api.dependencies import get_current_user
from src.auth.models import AuthenticatedUser
from src.auth.models import UserRole

client = TestClient(app, raise_server_exceptions=False)

def override_customer_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)


def test_chat_requires_authentication() -> None:
    response = client.post("/chat", json={"message": "What is the status of order ORD-10245?"})

    assert response.status_code == 401

def test_chat_rejects_empty_message() -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    try:
        response = client.post("/chat", json={"message": "   "})        
        data = response.json()

        assert response.status_code == 200
        assert data["response"] == "Please provide a message."
        assert data["thread_id"]
    finally:
        app.dependency_overrides.clear()


@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_returns_agent_response(mock_create_chat_model: MagicMock, mock_create_rag_service: MagicMock, mock_build_agent_graph: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = { "response": "The status of order ORD-10245 is SHIPPED." }

    mock_build_agent_graph.return_value = mock_graph

    try:
        response = client.post("/chat", json={"message": "What is the status of order ORD-10245?"})
        data = response.json()

        assert response.status_code == 200
        assert data["response"] == "The status of order ORD-10245 is SHIPPED."
        assert data["thread_id"]

        mock_create_chat_model.assert_called_once()
        mock_create_rag_service.assert_called_once()
        mock_build_agent_graph.assert_called_once()
        mock_graph.invoke.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_handles_agent_failure(mock_create_chat_model: MagicMock, mock_create_rag_service: MagicMock, mock_build_agent_graph: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()
    mock_graph.invoke.side_effect = RuntimeError("Agent execution failed")

    mock_build_agent_graph.return_value = mock_graph

    try:
        response = client.post("/chat", json={"message": "What is the status of order ORD-10245?"})

        assert response.status_code == 500
    finally:
        app.dependency_overrides.clear()
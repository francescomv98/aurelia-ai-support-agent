import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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


@patch("src.api.routes.chat.get_checkpointer")
@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_returns_agent_response(mock_create_chat_model: MagicMock, mock_create_rag_service: MagicMock, mock_build_agent_graph: MagicMock, mock_get_checkpointer: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"response": "The status of order ORD-10245 is SHIPPED."})

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
        mock_graph.ainvoke.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_handles_agent_failure(mock_create_chat_model: MagicMock, mock_create_rag_service: MagicMock, mock_build_agent_graph: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("Agent execution failed"))

    mock_build_agent_graph.return_value = mock_graph

    try:
        response = client.post("/chat", json={"message": "What is the status of order ORD-10245?"})

        assert response.status_code == 500
    finally:
        app.dependency_overrides.clear()


@patch("src.api.routes.chat.get_checkpointer")
@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_returns_approval_required(
    mock_create_chat_model: MagicMock,
    mock_create_rag_service: MagicMock,
    mock_build_agent_graph: MagicMock,
    mock_get_checkpointer: MagicMock,
) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "__interrupt__": [
                MagicMock(
                    value={
                        "type": "human_approval",
                        "action_type": "create_order",
                        "description": "Create an order for customer 1.",
                        "parameters": {
                            "items": [
                                {
                                    "product_code": "PROD-200",
                                    "quantity": 2,
                                }
                            ]
                        },
                    }
                )
            ]
        }
    )

    mock_build_agent_graph.return_value = mock_graph

    try:
        response = client.post(
            "/chat",
            json={"message": "Create an order for two PROD-200."},
        )

        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "approval_required"
        assert data["thread_id"]
        assert data["response"] is None

        assert data["approval"]["action_type"] == "create_order"
        assert data["approval"]["description"] == "Create an order for customer 1."
        assert data["approval"]["parameters"]["items"][0]["product_code"] == "PROD-200"

        mock_graph.ainvoke.assert_called_once()

    finally:
        app.dependency_overrides.clear()


@patch("src.api.routes.chat.get_checkpointer")
@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_resume_returns_agent_response(mock_create_chat_model: MagicMock, mock_create_rag_service: MagicMock, mock_build_agent_graph: MagicMock, mock_get_checkpointer: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()

    state_snapshot = MagicMock()
    state_snapshot.values = {"authenticated_user": override_customer_user()}
    state_snapshot.next = ("human_approval",)

    mock_graph.aget_state = AsyncMock(return_value=state_snapshot)

    mock_graph.ainvoke = AsyncMock(return_value={"response": "The order was created successfully."})

    mock_build_agent_graph.return_value = mock_graph

    try:
        response = client.post("/chat/resume",
            json={
                "thread_id": "test-thread-123",
                "decision": "APPROVED"
            }
        )

        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "completed"
        assert data["response"] == "The order was created successfully."
        assert data["thread_id"] == "test-thread-123"

        mock_graph.ainvoke.assert_called_once()

        call_args = mock_graph.ainvoke.call_args

        assert call_args.args[0].resume == "APPROVED"
        assert call_args.kwargs["config"]["configurable"]["thread_id"] == "test-thread-123"

    finally:
        app.dependency_overrides.clear()


@patch("src.api.routes.chat.get_checkpointer")
@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_resume_rejects_thread_owned_by_another_user(mock_create_chat_model: MagicMock, mock_create_rag_service: MagicMock, mock_build_agent_graph: MagicMock, mock_get_checkpointer: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()

    state_snapshot = MagicMock()
    state_snapshot.values = {"authenticated_user": AuthenticatedUser(user_id=999, customer_id=999, role=UserRole.CUSTOMER)}
    state_snapshot.next = ("human_approval")

    mock_graph.aget_state = AsyncMock(return_value=state_snapshot)

    mock_build_agent_graph.return_value = mock_graph

    try:
        response = client.post("/chat/resume",
            json={
                "thread_id": "another-user-thread",
                "decision": "APPROVED"
            }
        )

        data = response.json()

        assert response.status_code == 403
        assert data["detail"] == "You are not authorized to resume this chat thread."

        mock_graph.ainvoke.assert_not_called()

    finally:
        app.dependency_overrides.clear()


@patch("src.api.routes.chat.get_checkpointer")
@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_resume_rejects_unknown_thread(mock_create_chat_model: MagicMock, mock_create_rag_service: MagicMock, mock_build_agent_graph: MagicMock, mock_get_checkpointer: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()

    state_snapshot = MagicMock()
    state_snapshot.values = {}

    mock_graph.aget_state = AsyncMock(return_value=state_snapshot)

    mock_build_agent_graph.return_value = mock_graph

    try:
        response = client.post("/chat/resume",
            json={
                "thread_id": "unknown-thread",
                "decision": "APPROVED"
            }
        )

        data = response.json()

        assert response.status_code == 404
        assert data["detail"] == "Chat thread not found."

        mock_graph.ainvoke.assert_not_called()

    finally:
        app.dependency_overrides.clear()


@patch("src.api.routes.chat.get_checkpointer")
@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_resume_rejects_thread_without_pending_approval(mock_create_chat_model: MagicMock, mock_create_rag_service: MagicMock, mock_build_agent_graph: MagicMock, mock_get_checkpointer: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()

    state_snapshot = MagicMock()
    state_snapshot.values = {"authenticated_user": override_customer_user()}
    state_snapshot.next = ()

    mock_graph.aget_state = AsyncMock(return_value=state_snapshot)

    mock_build_agent_graph.return_value = mock_graph

    try:
        response = client.post("/chat/resume",
            json={
                "thread_id": "completed-thread",
                "decision": "APPROVED"
            }
        )

        data = response.json()

        assert response.status_code == 400
        assert data["detail"] == "Chat thread is not waiting for human approval."

        mock_graph.ainvoke.assert_not_called()

    finally:
        app.dependency_overrides.clear()


def test_chat_resume_requires_authentication() -> None:
    response = client.post("/chat/resume",
        json={
            "thread_id": "test-thread",
            "decision": "APPROVED"
        }
    )

    assert response.status_code == 401


def test_chat_resume_rejects_invalid_decision() -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    try:
        response = client.post("/chat/resume",
            json={
                "thread_id": "test-thread",
                "decision": "MAYBE"
            }
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


@patch("src.api.routes.chat.get_checkpointer")
@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_resume_rejects_thread_without_owner(mock_create_chat_model: MagicMock, mock_create_rag_service: MagicMock, mock_build_agent_graph: MagicMock, mock_get_checkpointer: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()

    state_snapshot = MagicMock()
    state_snapshot.values = {}
    state_snapshot.next = ("human_approval",)

    mock_graph.aget_state = AsyncMock(return_value=state_snapshot)
    mock_build_agent_graph.return_value = mock_graph

    try:
        response = client.post("/chat/resume",
            json={
                "thread_id": "invalid-owner-thread",
                "decision": "APPROVED"
            }
        )

        data = response.json()

        assert response.status_code == 404
        assert data["detail"] == "Chat thread not found."

        mock_graph.ainvoke.assert_not_called()

    finally:
        app.dependency_overrides.clear()


@patch("src.api.routes.chat.get_checkpointer")
@patch("src.api.routes.chat.build_agent_graph")
@patch("src.api.routes.chat.create_rag_service")
@patch("src.api.routes.chat.create_chat_model")
def test_chat_resume_with_rejection_returns_agent_response(mock_create_chat_model: MagicMock, mock_create_rag_service: MagicMock, mock_build_agent_graph: MagicMock, mock_get_checkpointer: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = override_customer_user

    mock_graph = MagicMock()

    state_snapshot = MagicMock()
    state_snapshot.values = {"authenticated_user": override_customer_user()}
    state_snapshot.next = ("human_approval")

    mock_graph.aget_state = AsyncMock(return_value=state_snapshot)

    mock_graph.ainvoke = AsyncMock(
        return_value={
            "tool_result": "The requested action was rejected.",
            "response": "The requested action was rejected."
        }
    )

    mock_build_agent_graph.return_value = mock_graph

    try:
        response = client.post("/chat/resume",
            json={
                "thread_id": "test-thread-rejected",
                "decision": "REJECTED"
            }
        )

        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "completed"
        assert data["response"] == "The requested action was rejected."
        assert data["thread_id"] == "test-thread-rejected"

        mock_graph.ainvoke.assert_called_once()

        call_args = mock_graph.ainvoke.call_args

        assert call_args.args[0].resume == "REJECTED"
        assert call_args.kwargs["config"]["configurable"]["thread_id"] == "test-thread-rejected"

    finally:
        app.dependency_overrides.clear()

@pytest.mark.parametrize("role", [UserRole.SUPPORT_AGENT, UserRole.ADMIN])
@pytest.mark.parametrize("path, payload", [
    ("/chat", {"message": "What is the status of order ORD-10245?"}),
    ("/chat/resume", {"thread_id": "thread-1", "decision": "APPROVED"}),
])
@patch("src.api.routes.chat.build_agent_graph")
def test_chat_endpoints_reject_staff_users(mock_build_agent_graph: MagicMock, path: str, payload: dict, role: UserRole) -> None:
    # The agent serves customers only; staff do not act on their behalf.
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id=10, customer_id=None, role=role)

    try:
        response = client.post(path, json=payload)

        assert response.status_code == 403
        mock_build_agent_graph.assert_not_called()
    finally:
        app.dependency_overrides.clear()

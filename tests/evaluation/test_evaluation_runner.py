from unittest.mock import AsyncMock, MagicMock
import pytest
from scripts.run_evaluation import (create_evaluation_state, execute_evaluation_case, evaluate_case)
from src.auth.models import AuthenticatedUser, UserRole
from src.services.exceptions import AuthorizationError

def create_test_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)


def test_create_evaluation_state() -> None:
    case = {
        "id": "RAG-001",
        "category": "rag",
        "question": "What is the maintenance interval for the AIS-200?",
        "expected": "2000 operating hours"
    }

    state = create_evaluation_state(case=case, user=create_test_user())

    assert state["user_query"] == case["question"]
    assert state["authenticated_user"].user_id == 1
    assert state["authenticated_user"].customer_id == 1
    assert state["route"] == "rag"
    assert state["retrieved_context"] == []
    assert state["rag_available"] is True
    assert state["tool_type"] is None
    assert state["pending_action"] is None
    assert state["tool_result"] == ""
    assert state["response"] == ""


@pytest.mark.anyio
async def test_execute_evaluation_case() -> None:
    mock_graph = MagicMock()

    mock_graph.ainvoke = AsyncMock(return_value={"response": "The AIS-200 maintenance interval is 2000 operating hours."})

    case = {
        "id": "RAG-001",
        "category": "rag",
        "question": "What is the maintenance interval for the AIS-200?",
        "expected": "2000 operating hours"
    }

    result = await execute_evaluation_case(agent_graph=mock_graph, case=case, user=create_test_user())

    assert result["response"] == "The AIS-200 maintenance interval is 2000 operating hours."

    mock_graph.ainvoke.assert_called_once()

    call_args = mock_graph.ainvoke.call_args

    state = call_args.args[0]
    config = call_args.kwargs["config"]

    assert state["user_query"] == case["question"]
    assert state["authenticated_user"].user_id == 1
    assert config["configurable"]["thread_id"] == "evaluation-RAG-001"


def test_evaluate_case_passes_when_expected_value_is_present() -> None:
    case = {
        "id": "RAG-001",
        "category": "rag",
        "question": "What is the maintenance interval for the AIS-200?",
        "expected": "2000 operating hours"
    }

    result = {"response": "The AIS-200 maintenance interval is 2000 operating hours."}

    passed, reason = evaluate_case(case, result)

    assert passed is True
    assert reason == "Expected RAG information found in agent response."


def test_evaluate_case_fails_when_expected_value_is_missing() -> None:
    case = {
        "id": "RAG-001",
        "category": "rag",
        "question": "What is the maintenance interval for the AIS-200?",
        "expected": "2000 operating hours"
    }

    result = {
        "response": "The AIS-200 maintenance interval is 1500 operating hours."
    }

    passed, reason = evaluate_case(case, result)

    assert passed is False
    assert reason == "Expected RAG information was not found."


def test_evaluate_case_fails_when_result_is_empty() -> None:
    case = {
        "id": "RAG-001",
        "category": "rag",
        "question": "What is the maintenance interval for the AIS-200?",
        "expected": "2000 operating hours"
    }

    result = {}

    passed, reason = evaluate_case(case, result)

    assert passed is False
    assert reason == "Agent returned an empty result."


def test_evaluate_hitl_case_passes_when_approval_is_requested() -> None:
    case = {
        "id": "HITL-001",
        "category": "hitl",
        "question": "Create an order for 2 AIS-200 machines.",
        "expected": "human approval"
    }

    result = {
        "__interrupt__": [
            {
                "value": {
                    "type": "human_approval",
                    "action_type": "create_order"
                }
            }
        ]
    }

    passed, reason = evaluate_case(case, result)

    assert passed is True
    assert reason == "Human approval was requested."


def test_evaluate_hitl_case_fails_when_approval_is_missing() -> None:
    case = {
        "id": "HITL-001",
        "category": "hitl",
        "question": "Create an order for 2 AIS-200 machines.",
        "expected": "human approval"
    }

    result = {"response": "The order was created."}

    passed, reason = evaluate_case(case, result)

    assert passed is False
    assert reason == "Human approval was not requested."


def test_evaluate_authorization_accepts_authorized_result() -> None:
    case = {
        "id": "AUTH-001",
        "category": "authorization",
        "question": "Show me order ORD-10245.",
        "expected": "authorized"
    }

    result = {"response": "The user is authorized to access this order."}

    passed, reason = evaluate_case(case, result)

    assert passed is True
    assert reason == "Authorized request completed successfully."


def test_evaluate_authorization_accepts_rejected_result() -> None:
    case = {
        "id": "AUTH-002",
        "category": "authorization",
        "question": "Show me order ORD-10245.",
        "expected": "rejected"
    }

    result = {"error": AuthorizationError("Customer users cannot access another customer's resources.")}

    passed, reason = evaluate_case(case, result)

    assert passed is True
    assert reason == "Unauthorized request was rejected by authorization controls."


def test_evaluate_hybrid_requires_all_expected_values() -> None:
    case = {
        "id": "HYBRID-001",
        "category": "hybrid",
        "question": "How much time remains before maintenance?",
        "expected": "1734, 2000, 266"
    }

    result = {
        "response": (
            "The machine has 1734 operating hours. "
            "The maintenance interval is 2000 operating hours. "
            "There are 266 operating hours remaining."
        )
    }

    passed, reason = evaluate_case(case, result)

    assert passed is True
    assert reason == "All expected hybrid information was found."


def test_evaluate_hybrid_fails_when_one_value_is_missing() -> None:
    case = {
        "id": "HYBRID-001",
        "category": "hybrid",
        "question": "How much time remains before maintenance?",
        "expected": "1734, 2000, 266"
    }

    result = {
        "response": (
            "The machine has 1734 operating hours. "
            "The maintenance interval is 2000 operating hours."
        )
    }

    passed, reason = evaluate_case(case, result)

    assert passed is False
    assert "266" in reason
from unittest.mock import MagicMock
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.evaluation.evaluator import (evaluate_authorization, evaluate_case, evaluate_edge, evaluate_hitl, evaluate_hybrid, evaluate_rag, evaluate_tool, evaluate_security)
from src.services.exceptions import AuthorizationError

def create_test_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)


def test_evaluate_rag_success() -> None:
    success, reason = evaluate_rag(
        expected="2000 operating hours",
        actual="The AIS-200 maintenance interval is 2000 operating hours."
    )

    assert success is True
    assert reason == "Expected RAG information found in agent response."


def test_evaluate_rag_failure() -> None:
    success, reason = evaluate_rag(
        expected="2000 operating hours",
        actual="The AIS-200 maintenance interval is 1500 operating hours."
    )

    assert success is False
    assert reason == "Expected RAG information was not found."


def test_evaluate_tool_success() -> None:
    success, reason = evaluate_tool(
        expected="AIS2-2025-00142, AIS-200, 1734 operating hours",
        actual="Machine AIS2-2025-00142 is an AIS-200 with 1734 operating hours."
    )

    assert success is True
    assert reason == "All expected tool information was found."


def test_evaluate_tool_failure() -> None:
    success, reason = evaluate_tool(
        expected="AIS2-2025-00142, AIS-200, 1734 operating hours",
        actual="Machine AIS2-2025-00142 is an AIS-200 with 1600 operating hours."
    )

    assert success is False
    assert "1734 hours" in reason


def test_evaluate_authorization_authorized() -> None:
    result = {
        "response": "Order ORD-10245 is SHIPPED.",
        "tool_result": "Order ORD-10245 is SHIPPED."
    }

    success, reason = evaluate_authorization(expected="AUTHORIZED", result=result)

    assert success is True
    assert reason == "Authorized request completed successfully."


def test_evaluate_authorization_rejected() -> None:
    error = AuthorizationError("Customer users cannot access another customer's resources.")

    result = {"error": error}

    success, reason = evaluate_authorization(expected="REJECTED", result=result)

    assert success is True
    assert reason == "Unauthorized request was rejected by authorization controls."


def test_evaluate_authorization_failure() -> None:
    result = {"response": "Order not found."}

    success, reason = evaluate_authorization(expected="REJECTED", result=result)

    assert success is True
    assert reason == "Unauthorized request was rejected without revealing protected resource information."


def test_evaluate_hitl_success() -> None:
    interrupt = MagicMock()

    result = {"__interrupt__": [interrupt]}

    success, reason = evaluate_hitl(result)

    assert success is True
    assert reason == "Human approval was requested."


def test_evaluate_hitl_failure() -> None:
    result = {"response": "The order was created."}

    success, reason = evaluate_hitl(result)

    assert success is False
    assert reason == "Human approval was not requested."


def test_evaluate_hybrid_success() -> None:
    success, reason = evaluate_hybrid(
        expected="AIS2-2025-00142, AIS-200, 1734 operating hours, 2000 operating hours, 266 operating hours",
        actual="Machine AIS2-2025-00142 is an AIS-200 with 1734 operating hours. The maintenance interval is 2000 operating hours. Maintenance is not yet due and 266 operating hours remain."
    )

    assert success is True
    assert reason == "All expected hybrid information was found."


def test_evaluate_hybrid_failure() -> None:
    success, reason = evaluate_hybrid(
        expected="AIS2-2025-00142, AIS-200, 1734 operating hours, 2000 operating hours, 266 operating hours",
        actual="Machine AIS2-2025-00142 is an AIS-200 with 1734 operating hours. The maintenance interval is 2000 operating hours."
    )

    assert success is False
    assert "266 hours" in reason


def test_evaluate_edge_order_not_found_success() -> None:
    success, reason = evaluate_edge(
        expected="Order not found",
        actual="Order not found."
    )

    assert success is True
    assert reason == "Expected edge-case behavior was found."


def test_evaluate_edge_order_not_found_failure() -> None:
    success, reason = evaluate_edge(
        expected="Order not found",
        actual="Order ORD-99999 is SHIPPED."
    )

    assert success is False
    assert reason == "Expected order-not-found behavior was not found."


def test_evaluate_edge_clarification_success() -> None:
    success, reason = evaluate_edge(
        expected="clarification",
        actual="Could you provide more information about what you need help with?"
    )

    assert success is True
    assert reason == "Agent requested clarification."


def test_evaluate_edge_clarification_failure() -> None:
    success, reason = evaluate_edge(
        expected="clarification",
        actual="The requested order does not exist."
    )

    assert success is False
    assert reason == "Agent did not request clarification."


def test_evaluate_case_rag() -> None:
    case = {
        "id": "RAG-001",
        "category": "rag",
        "question": "What is the maintenance interval for the AIS-200?",
        "expected": "2000 operating hours"
    }

    result = {
        "response": "The AIS-200 maintenance interval is 2000 operating hours.",
        "tool_result": ""
    }

    success, reason = evaluate_case(case, result)

    assert success is True
    assert reason == "Expected RAG information found in agent response."


def test_evaluate_case_tool() -> None:
    case = {
        "id": "TOOL-005",
        "category": "tool",
        "question": "What is the status of machine AIS2-2025-00142?",
        "expected": "AIS2-2025-00142, AIS-200, 1734 operating hours"
    }

    result = {
        "response": "Machine AIS2-2025-00142 is an AIS-200 with 1734 operating hours.",
        "tool_result": ""
    }

    success, reason = evaluate_case(case, result)

    assert success is True
    assert reason == "All expected tool information was found."


def test_evaluate_case_authorization() -> None:
    case = {
        "id": "AUTH-002",
        "category": "authorization",
        "question": "What is the status of order ORD-10245?",
        "authenticated_customer_id": 2,
        "expected": "REJECTED"
    }

    result = {"error": AuthorizationError("Customer users cannot access another customer's resources.")}

    success, reason = evaluate_case(case, result)

    assert success is True
    assert reason == "Unauthorized request was rejected by authorization controls."


def test_evaluate_case_hitl() -> None:
    case = {
        "id": "HITL-001",
        "category": "hitl",
        "question": "Create an order for 2 AIS-200 machines.",
        "expected": "Human approval is required before executing the write operation."
    }

    result = {"__interrupt__": [MagicMock()]}

    success, reason = evaluate_case(case, result)

    assert success is True
    assert reason == "Human approval was requested."


def test_evaluate_case_hybrid() -> None:
    case = {
        "id": "HYBRID-001",
        "category": "hybrid",
        "question": "What is the maintenance status of machine AIS2-2025-00142 and what is the recommended maintenance interval for its AIS-200 model?",
        "expected": "AIS2-2025-00142, AIS-200, 1734 operating hours, 2000 operating hours, 266 operating hours"
    }

    result = {
        "response": (
            "Machine AIS2-2025-00142 is an AIS-200 with "
            "1734 operating hours. The current maintenance interval "
            "is 2000 operating hours and 266 operating hours remain."
        ),
        "tool_result": ""
    }

    success, reason = evaluate_case(case, result)

    assert success is True
    assert reason == "All expected hybrid information was found."


def test_evaluate_case_edge() -> None:
    case = {
        "id": "EDGE-001",
        "category": "edge",
        "question": "What is the status of an unknown order ORD-99999?",
        "expected": "Order not found"
    }

    result = {
        "response": "Order not found.",
        "tool_result": ""
    }

    success, reason = evaluate_case(case, result)

    assert success is True
    assert reason == "Expected edge-case behavior was found."


def test_evaluate_security_rejected_by_authorization() -> None:
    result = {"error": AuthorizationError("The authenticated user is not authorized to perform this action.")}

    success, reason = evaluate_security(expected="REJECTED", result=result)

    assert success is True
    assert reason == "Security-sensitive request was rejected by authorization controls."


def test_evaluate_security_rejected_by_safe_response() -> None:
    result = {"response": "The authenticated user is not authorized to access this customer."}

    success, reason = evaluate_security(expected="REJECTED", result=result)

    assert success is True
    assert reason == "Security-sensitive request was safely rejected."


def test_evaluate_security_failure() -> None:
    result = {"response": "Customer CUST-002 information is available."}

    success, reason = evaluate_security(expected="REJECTED", result=result)

    assert success is False
    assert reason == "Security-sensitive request was not rejected by security controls."
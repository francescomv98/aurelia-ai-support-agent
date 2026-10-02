from src.agent.action_preparation import prepare_action
from src.auth.models import AuthenticatedUser, UserRole
from unittest.mock import MagicMock

def create_state(user_query: str) -> dict:
    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    return {
        "user_query": user_query,
        "authenticated_user": user,
        "route": "tool",
        "retrieved_context": [],
        "tool_type": None,
        "pending_action": None,
        "tool_result": "",
        "response": ""
    }


def test_prepare_create_order_action():
    state = create_state("Create an order for 2 AIS-200 machines.")

    chat_model = MagicMock()

    action = MagicMock()
    item = MagicMock()
    item.product_code = "AIS-200"
    item.quantity = 2

    action.items = [item]

    chat_model.with_structured_output.return_value.invoke.return_value = action

    result = prepare_action(state, chat_model=chat_model)

    assert result["pending_action"] is not None
    assert result["pending_action"].action_type == "create_order"

    assert result["pending_action"].parameters == {
        "items": [
            {
                "product_code": "AIS-200",
                "quantity": 2
            }
        ]
    }


def test_prepare_cancel_order_action():
    state = create_state("Please cancel order ORD-10245.")

    result = prepare_action(state)

    assert result["pending_action"] is not None
    assert result["pending_action"].action_type == "cancel_order"


def test_prepare_create_support_ticket_action():
    state = create_state("Create a support ticket for machine AIS2-2025-00142.")

    result = prepare_action(state)

    assert result["pending_action"] is not None
    assert result["pending_action"].action_type == "create_support_ticket"


def test_prepare_update_support_ticket_action():
    state = create_state("Update support ticket TCK-5021.")

    result = prepare_action(state)

    assert result["pending_action"] is not None
    assert result["pending_action"].action_type == "update_support_ticket"


def test_prepare_action_returns_none_for_read_request():
    state = create_state("What is the status of order ORD-10245?")

    result = prepare_action(state)

    assert result["pending_action"] is None
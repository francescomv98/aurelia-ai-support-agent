import pytest
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.security.authorization import (require_customer_access, require_role)
from unittest.mock import MagicMock
from src.agent.authorization import authorize_action
from src.agent.state import PendingAction
from src.services.exceptions import AuthorizationError

def create_user(user_id: int = 1, customer_id: int | None = 1, role: UserRole = UserRole.CUSTOMER) -> AuthenticatedUser:
    return AuthenticatedUser(user_id=user_id, customer_id=customer_id, role=role)


def test_customer_can_access_own_customer() -> None:
    user = create_user(customer_id=1, role=UserRole.CUSTOMER)

    require_customer_access(user, customer_id=1)


def test_customer_cannot_access_another_customer() -> None:
    user = create_user(customer_id=1, role=UserRole.CUSTOMER)

    with pytest.raises(AuthorizationError, match="not authorized"):
        require_customer_access(user, customer_id=2)


@pytest.mark.parametrize("role", [UserRole.SUPPORT_AGENT, UserRole.ADMIN])
def test_staff_cannot_access_customer_data(role: UserRole) -> None:
    # The agent serves customers only; staff do not act on their behalf.
    user = create_user(customer_id=None, role=role)

    with pytest.raises(AuthorizationError, match="not authorized"):
        require_customer_access(user, customer_id=2)


def test_customer_without_customer_context_is_rejected() -> None:
    user = create_user(customer_id=None, role=UserRole.CUSTOMER)

    with pytest.raises(AuthorizationError, match="not authorized"):
        require_customer_access(user, customer_id=1)


def test_allowed_role_is_accepted() -> None:
    user = create_user(role=UserRole.CUSTOMER)

    require_role(user, allowed_roles={UserRole.CUSTOMER})


def test_disallowed_role_is_rejected() -> None:
    user = create_user(role=UserRole.CUSTOMER)

    with pytest.raises(AuthorizationError, match="not authorized"):
        require_role(user, allowed_roles={UserRole.ADMIN})


def create_state(approval_result: str):
    return {
        "user_query": "Create an order for 2 AIS-200 machines.",
        "authenticated_user": MagicMock(
            user_id=1,
            customer_id=1,
            role=UserRole.CUSTOMER
        ),
        "route": "tool",
        "retrieved_context": [],
        "tool_type": "order",
        "pending_action": PendingAction(
            action_type="create_order",
            description="Create an order for 2 AIS-200 machines.",
            parameters={
                "items": [
                    {
                        "product_code": "AIS-200",
                        "quantity": 2
                    }
                ]
            }
        ),
        "tool_result": approval_result,
        "response": ""
    }


def test_authorize_approved_action():
    state = create_state("APPROVED")

    result = authorize_action(state)

    assert result["tool_result"] == "APPROVED"


def test_authorize_rejected_action():
    state = create_state("REJECTED")

    result = authorize_action(state)

    assert result["tool_result"] == "REJECTED"


def test_authorize_without_pending_action():
    state = create_state("APPROVED")
    state["pending_action"] = None

    with pytest.raises(ValueError, match="No pending action"):
        authorize_action(state)


def test_authorize_action_rejects_foreign_customer_id():
    state = create_state("The requested action was approved.")
    state["authenticated_user"] = create_user(customer_id=1)
    state["pending_action"].parameters["customer_id"] = 2

    with pytest.raises(AuthorizationError, match="not authorized"):
        authorize_action(state)


def test_authorize_action_accepts_own_customer_id():
    state = create_state("The requested action was approved.")
    state["authenticated_user"] = create_user(customer_id=1)
    state["pending_action"].parameters["customer_id"] = 1

    assert authorize_action(state) is state

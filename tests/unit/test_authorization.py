import pytest
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.security.authorization import (require_customer_access, require_role)

def create_user(user_id: int = 1, customer_id: int | None = 1, role: UserRole = UserRole.CUSTOMER) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=user_id,
        customer_id=customer_id,
        role=role
    )


def test_customer_can_access_own_customer() -> None:
    user = create_user(customer_id=1, role=UserRole.CUSTOMER)

    require_customer_access(user, customer_id=1)


def test_customer_cannot_access_another_customer() -> None:
    user = create_user(customer_id=1, role=UserRole.CUSTOMER)

    with pytest.raises(PermissionError, match="not authorized"):
        require_customer_access(user, customer_id=2)


def test_support_agent_can_access_any_customer() -> None:
    user = create_user(customer_id=None, role=UserRole.SUPPORT_AGENT)

    require_customer_access(user, customer_id=2)


def test_admin_can_access_any_customer() -> None:
    user = create_user(customer_id=None, role=UserRole.ADMIN)

    require_customer_access(user, customer_id=999)


def test_allowed_role_is_accepted() -> None:
    user = create_user(role=UserRole.CUSTOMER)

    require_role(user, allowed_roles={UserRole.CUSTOMER})


def test_disallowed_role_is_rejected() -> None:
    user = create_user(role=UserRole.CUSTOMER)

    with pytest.raises(PermissionError, match="not authorized"):
        require_role(user, allowed_roles={UserRole.ADMIN})
from unittest.mock import MagicMock, patch
import pytest
from src.auth.models import AuthenticatedUser
from src.auth.service import AuthenticationService
from src.database.models import Role, User

def create_user(username: str = "alfa.support", is_active: bool = True) -> User:
    user = User(
        id=1,
        username=username,
        password_hash="hashed-password",
        is_active=is_active,
        customer_id=1,
        role_id=1
    )

    user.role = Role(id=1, name="CUSTOMER")

    return user


def test_authenticate_returns_access_token_for_valid_credentials() -> None:
    db = MagicMock()
    user = create_user()

    db.scalar.return_value = user

    with (patch("src.auth.service.verify_password", return_value=True), patch("src.auth.service.create_access_token", return_value="test-access-token") as create_token):
        service = AuthenticationService(db)

        token = service.authenticate(username="alfa.support", password="AureliaDemo123!")

    assert token == "test-access-token"

    create_token.assert_called_once_with(AuthenticatedUser(user_id=1, customer_id=1, role="CUSTOMER"))


def test_authenticate_rejects_invalid_password() -> None:
    db = MagicMock()
    user = create_user()

    db.scalar.return_value = user

    with patch("src.auth.service.verify_password", return_value=False):
        service = AuthenticationService(db)

        with pytest.raises(ValueError, match="Invalid username or password."):
            service.authenticate(username="alfa.support", password="WrongPassword123!")


def test_authenticate_rejects_unknown_username() -> None:
    db = MagicMock()
    db.scalar.return_value = None

    service = AuthenticationService(db)

    with pytest.raises(ValueError, match="Invalid username or password."):
        service.authenticate(username="unknown.user", password="AureliaDemo123!")


def test_authenticate_rejects_inactive_user() -> None:
    db = MagicMock()
    user = create_user(is_active=False)

    db.scalar.return_value = user

    with pytest.raises(ValueError, match="Invalid username or password."):
        service = AuthenticationService(db)

        service.authenticate(username="alfa.support", password="AureliaDemo123!")


def test_authenticate_rejects_empty_username() -> None:
    db = MagicMock()
    service = AuthenticationService(db)

    with pytest.raises(ValueError, match="Username cannot be empty."):
        service.authenticate(username="", password="AureliaDemo123!")


def test_authenticate_rejects_empty_password() -> None:
    db = MagicMock()
    service = AuthenticationService(db)

    with pytest.raises(ValueError, match="Password cannot be empty."):
        service.authenticate(username="alfa.support", password="")
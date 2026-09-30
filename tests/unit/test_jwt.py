import pytest
from src.auth.jwt import create_access_token, decode_access_token
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole

def test_create_and_decode_access_token(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    token = create_access_token(user)

    decoded_user = decode_access_token(token)

    assert decoded_user.user_id == 1
    assert decoded_user.customer_id == 1
    assert decoded_user.role == UserRole.CUSTOMER


def test_invalid_token_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")

    with pytest.raises(ValueError, match="Invalid access token"):
        decode_access_token("invalid-token")


def test_empty_token_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")

    with pytest.raises(ValueError, match="Access token cannot be empty"):
        decode_access_token("")


def test_token_signed_with_wrong_secret_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "secret-one")

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    token = create_access_token(user)

    monkeypatch.setenv("JWT_SECRET_KEY", "secret-two")

    with pytest.raises(ValueError, match="Invalid access token"):
        decode_access_token(token)


def test_expired_token_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "-1")

    with pytest.raises(RuntimeError, match="must be greater than zero"):
        create_access_token(
            AuthenticatedUser(
                user_id=1,
                customer_id=1,
                role=UserRole.CUSTOMER
            )
        )
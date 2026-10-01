import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from src.api.dependencies import get_current_user
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole

def test_get_current_user_returns_authenticated_user(monkeypatch) -> None:
    expected_user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    def fake_decode_access_token(token: str) -> AuthenticatedUser:
        assert token == "valid-token"
        return expected_user

    monkeypatch.setattr("src.api.dependencies.decode_access_token", fake_decode_access_token)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

    result = get_current_user(credentials)

    assert result == expected_user


def test_get_current_user_rejects_invalid_token(monkeypatch) -> None:
    def fake_decode_access_token(token: str) -> AuthenticatedUser:
        raise ValueError("Invalid access token.")

    monkeypatch.setattr("src.api.dependencies.decode_access_token", fake_decode_access_token)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid access token."
    assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"
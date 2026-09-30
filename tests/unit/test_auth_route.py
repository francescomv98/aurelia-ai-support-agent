from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_login_returns_access_token(monkeypatch) -> None:
    def fake_authenticate(self, username: str, password: str) -> str:
        assert username == "alfa.support"
        assert password == "AureliaDemo123!"
        return "test-access-token"

    monkeypatch.setattr("src.api.routes.auth.AuthenticationService.authenticate", fake_authenticate)

    response = client.post("/auth/login", json={ "username": "alfa.support", "password": "AureliaDemo123!" })

    assert response.status_code == 200
    assert response.json() == { "access_token": "test-access-token", "token_type": "bearer" }


def test_login_rejects_invalid_credentials(monkeypatch) -> None:
    def fake_authenticate(self, username: str, password: str) -> str:
        raise ValueError("Invalid username or password.")

    monkeypatch.setattr("src.api.routes.auth.AuthenticationService.authenticate", fake_authenticate)

    response = client.post("/auth/login", json={ "username": "alfa.support", "password": "WrongPassword123!" })

    assert response.status_code == 401
    assert response.json() == { "detail": "Invalid username or password." }


def test_login_rejects_missing_username() -> None:
    response = client.post("/auth/login", json={ "password": "AureliaDemo123!" })

    assert response.status_code == 422


def test_login_rejects_missing_password() -> None:
    response = client.post("/auth/login", json={ "username": "alfa.support" })

    assert response.status_code == 422
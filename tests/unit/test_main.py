from fastapi.testclient import TestClient
from main import app
from src.security.rate_limiter import RateLimiter
from src.services.exceptions import (ApplicationError, AuthorizationError, DatabaseError, ExternalServiceError, LLMError, ValidationError)

client = TestClient(app, raise_server_exceptions=False)


def test_validation_error_returns_400():
    @app.get("/test-validation-error")
    def test_endpoint():
        raise ValidationError("Invalid input.")

    response = client.get("/test-validation-error")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid input."}


def test_authorization_error_returns_403():
    @app.get("/test-authorization-error")
    def test_endpoint():
        raise AuthorizationError("User is not authorized.")

    response = client.get("/test-authorization-error")

    assert response.status_code == 403
    assert response.json() == {"detail": "User is not authorized."}


def test_database_error_returns_500():
    @app.get("/test-database-error")
    def test_endpoint():
        raise DatabaseError("Database connection failed.")

    response = client.get("/test-database-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "A database error occurred."}


def test_llm_error_returns_503():
    @app.get("/test-llm-error")
    def test_endpoint():
        raise LLMError("OpenAI request failed.")

    response = client.get("/test-llm-error")

    assert response.status_code == 503
    assert response.json() == {"detail": "The AI service is temporarily unavailable."}


def test_external_service_error_returns_503():
    @app.get("/test-external-service-error")
    def test_endpoint():
        raise ExternalServiceError("External service failed.")

    response = client.get("/test-external-service-error")

    assert response.status_code == 503
    assert response.json() == {"detail": "An external service is temporarily unavailable."}


def test_application_error_returns_500():
    @app.get("/test-application-error")
    def test_endpoint():
        raise ApplicationError("Application failure.")

    response = client.get("/test-application-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "An application error occurred."}


def test_unexpected_error_returns_500():
    @app.get("/test-unexpected-error")
    def test_endpoint():
        raise RuntimeError("Unexpected internal failure.")

    response = client.get("/test-unexpected-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "An internal server error occurred."}


def test_rate_limit_returns_429_when_limit_is_exceeded():
    app.state.rate_limiter = RateLimiter(max_requests=2, window_seconds=60)

    client = TestClient(app, raise_server_exceptions=False)

    first_response = client.get("/docs")
    second_response = client.get("/docs")
    third_response = client.get("/docs")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert third_response.status_code == 429

    assert third_response.json() == {"detail": "Too many requests. Please try again later."}
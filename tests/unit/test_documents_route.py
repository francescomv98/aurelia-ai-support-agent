from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from main import app
from src.api.dependencies import get_current_user
from src.auth.models import AuthenticatedUser, UserRole
from src.security.rate_limiter import RateLimiter
from src.services.document_review_service import DocumentRecord, ReviewResult
from src.services.exceptions import ExternalServiceError, NotFoundError

client = TestClient(app, raise_server_exceptions=False)

DOCUMENT_ID = "5d3ce3c9-21d8-580b-8705-a3bc8ca4e705"


def as_user(role: UserRole) -> None:
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id=1, customer_id=1 if role == UserRole.CUSTOMER else None, role=role)


@pytest.fixture(autouse=True)
def isolate_app():
    # The app-wide rate limiter is shared by every route test: these requests
    # must not use up the quota and make later tests fail with 429.
    original_limiter = app.state.rate_limiter
    app.state.rate_limiter = RateLimiter(max_requests=1000, window_seconds=60)

    yield

    app.state.rate_limiter = original_limiter
    app.dependency_overrides.clear()


def test_admin_document_endpoints_require_authentication() -> None:
    assert client.get("/admin/documents/review-due").status_code == 401
    assert client.post(f"/admin/documents/{DOCUMENT_ID}/review").status_code == 401


@pytest.mark.parametrize("role", [UserRole.CUSTOMER, UserRole.SUPPORT_AGENT])
@patch("src.api.routes.documents.create_document_review_service")
def test_admin_document_endpoints_reject_non_admins(mock_create_service: MagicMock, role: UserRole) -> None:
    as_user(role)

    assert client.get("/admin/documents/review-due").status_code == 403
    assert client.post(f"/admin/documents/{DOCUMENT_ID}/review").status_code == 403
    mock_create_service.assert_not_called()


@patch("src.api.routes.documents.create_document_review_service")
def test_review_due_lists_documents(mock_create_service: MagicMock) -> None:
    as_user(UserRole.ADMIN)
    mock_create_service.return_value.documents_due_for_review.return_value = []

    response = client.get("/admin/documents/review-due", params={"days": 180})

    assert response.status_code == 200
    assert response.json() == []
    interval = mock_create_service.return_value.documents_due_for_review.call_args.kwargs["interval"]
    assert interval.days == 180


def test_review_due_rejects_invalid_interval() -> None:
    as_user(UserRole.ADMIN)

    assert client.get("/admin/documents/review-due", params={"days": 0}).status_code == 422


@patch("src.api.routes.documents.create_document_review_service")
def test_mark_document_reviewed(mock_create_service: MagicMock) -> None:
    as_user(UserRole.ADMIN)
    mock_create_service.return_value.mark_reviewed.return_value = ReviewResult(
        document=DocumentRecord(document_id=DOCUMENT_ID, source="warranty_policy.pdf", title="Warranty Policy", category="policies",
                                date=None, valid=True, reviewed_at="2026-11-12T10:00:00Z"),
        chunk_count=7
    )

    response = client.post(f"/admin/documents/{DOCUMENT_ID}/review")

    assert response.status_code == 200
    assert response.json()["chunk_count"] == 7
    assert response.json()["document"]["reviewed_at"] == "2026-11-12T10:00:00Z"
    mock_create_service.return_value.mark_reviewed.assert_called_once_with(DOCUMENT_ID)


@patch("src.api.routes.documents.create_document_review_service")
def test_mark_unknown_document_reviewed_returns_404(mock_create_service: MagicMock) -> None:
    as_user(UserRole.ADMIN)
    mock_create_service.return_value.mark_reviewed.side_effect = NotFoundError("Document x not found.")

    response = client.post("/admin/documents/x/review")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document x not found."


@patch("src.api.routes.documents.create_document_review_service")
def test_failed_reingestion_tells_the_admin_the_review_was_saved(mock_create_service: MagicMock) -> None:
    as_user(UserRole.ADMIN)
    mock_create_service.return_value.mark_reviewed.side_effect = ExternalServiceError("The review was saved, but the document could not be re-indexed.")

    response = client.post(f"/admin/documents/{DOCUMENT_ID}/review")

    assert response.status_code == 503
    assert "review was saved" in response.json()["detail"]

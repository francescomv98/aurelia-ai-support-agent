import os
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.api.dependencies import get_current_user
from src.app_logging.logger import logger
from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.rag.embedding import create_embeddings
from src.rag.vector_store import VectorStore
from src.security.authorization import require_role
from src.services.document_review_service import REVIEW_INTERVAL, DocumentReviewService, ReviewDueDocument, ReviewResult
from src.services.exceptions import ExternalServiceError

router = APIRouter(prefix="/admin/documents", tags=["admin"])


def create_vector_store() -> VectorStore:
    """Create the vector store used to re-ingest a reviewed document."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    return VectorStore(connection=database_url, embeddings=create_embeddings())


def create_document_review_service() -> DocumentReviewService:
    return DocumentReviewService(vector_store_factory=create_vector_store)


# Plain "def" endpoints: FastAPI runs them in a worker thread, so the blocking
# PDF parsing, embedding call and database writes do not stall the event loop.

@router.get("/review-due", response_model=list[ReviewDueDocument])
def documents_due_for_review(days: int = Query(REVIEW_INTERVAL.days, ge=1, le=3650, description="Review interval in days."),
                             current_user: AuthenticatedUser = Depends(get_current_user)) -> list[ReviewDueDocument]:
    """List the valid documents not reviewed for more than `days` days (default 365)."""

    require_role(current_user, {UserRole.ADMIN})

    logger.info("Review-due documents requested", user_id=current_user.user_id, days=days)

    return create_document_review_service().documents_due_for_review(interval=timedelta(days=days))


@router.post("/{document_id}/review", response_model=ReviewResult)
def mark_document_reviewed(document_id: str, current_user: AuthenticatedUser = Depends(get_current_user)) -> ReviewResult:
    """Record that the document was reviewed now, and re-ingest it so its chunks carry the new review date."""

    require_role(current_user, {UserRole.ADMIN})

    logger.info("Document review submitted", user_id=current_user.user_id, document_id=document_id)

    try:
        return create_document_review_service().mark_reviewed(document_id)
    except ExternalServiceError as exc:
        # The generic handler hides the message; the admin needs to know the review itself was saved.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

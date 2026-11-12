"""Review tracking for the knowledge-base documents.

The owner manifest (data/documents/metadata.json) stays the single source of
truth: recording a review writes reviewed_at there and then re-ingests only the
reviewed document, so its chunks in the vector store carry the new value and a
later full ingestion keeps it.
"""

import threading
from collections.abc import Callable
from datetime import date as Date, datetime, time, timedelta, timezone
from pathlib import Path
from pydantic import BaseModel
from src.app_logging.logger import logger
from src.rag.chunker import DocumentChunker
from src.rag.document_loader import DocumentLoader
from src.rag.document_metadata import (MANIFEST_FILE_NAME, DocumentInfo, document_id_from_source, document_title,
                                       load_manifest, save_manifest)
from src.rag.vector_store import VectorStore
from src.services.exceptions import ExternalServiceError, NotFoundError

DOCUMENTS_DIRECTORY = Path("data/documents")
REVIEW_INTERVAL = timedelta(days=365)

# The manifest is read, changed and written back whole: two concurrent reviews
# would otherwise each write their own copy and one review would be lost.
_manifest_lock = threading.Lock()


class DocumentRecord(BaseModel):
    """A knowledge-base document and its owner-managed information."""

    document_id: str
    source: str
    title: str
    category: str
    date: Date | None
    valid: bool
    reviewed_at: datetime | None


class ReviewDueDocument(DocumentRecord):
    """A document whose review is overdue."""

    review_reference: datetime | None
    """Last review, or the effective date if it was never reviewed; None when neither is known."""
    days_since_reference: int | None


class ReviewResult(BaseModel):
    """Outcome of recording a review."""

    document: DocumentRecord
    chunk_count: int
    """Chunks of the document now in the vector store."""


def review_reference(info: DocumentInfo) -> datetime | None:
    """Point in time the next review is counted from: the last review, else the effective date (midnight UTC)."""

    if info.reviewed_at is not None:
        return info.reviewed_at

    if info.date is not None:
        return datetime.combine(info.date, time.min, tzinfo=timezone.utc)

    return None


class DocumentReviewService:
    """List documents due for review and record reviews."""

    def __init__(self, documents_directory: Path = DOCUMENTS_DIRECTORY, vector_store_factory: Callable[[], VectorStore] | None = None,
                 loader: DocumentLoader | None = None, chunker: DocumentChunker | None = None) -> None:
        self.documents_directory = documents_directory
        # A factory, so listing due documents needs neither the database nor an OpenAI key.
        self.vector_store_factory = vector_store_factory
        self.loader = loader or DocumentLoader()
        self.chunker = chunker or DocumentChunker()

    @property
    def manifest_path(self) -> Path:
        return self.documents_directory / MANIFEST_FILE_NAME

    def _pdf_files(self) -> list[Path]:
        return sorted(self.documents_directory.rglob("*.pdf"))

    @staticmethod
    def _record(pdf_path: Path, info: DocumentInfo) -> DocumentRecord:
        return DocumentRecord(
            document_id=document_id_from_source(pdf_path.name),
            source=pdf_path.name,
            title=document_title(pdf_path.name),
            category=pdf_path.parent.name,
            date=info.date,
            valid=info.valid,
            reviewed_at=info.reviewed_at
        )

    def documents_due_for_review(self, now: datetime | None = None, interval: timedelta = REVIEW_INTERVAL) -> list[ReviewDueDocument]:
        """Valid documents not reviewed for longer than interval, most overdue first.

        A document never reviewed counts from its effective date; one with
        neither date is always due. Withdrawn documents (valid: false) are not
        listed: nobody reads them, so there is nothing to keep current.
        """

        now = now or datetime.now(timezone.utc)
        manifest = load_manifest(self.manifest_path)
        due: list[ReviewDueDocument] = []

        for pdf_path in self._pdf_files():
            info = manifest.get(pdf_path.name, DocumentInfo())

            if not info.valid:
                continue

            reference = review_reference(info)

            if reference is not None and now - reference <= interval:
                continue

            due.append(ReviewDueDocument(
                **self._record(pdf_path, info).model_dump(),
                review_reference=reference,
                days_since_reference=(now - reference).days if reference else None
            ))

        # Unknown reference first (most urgent), then the oldest.
        due.sort(key=lambda document: (document.review_reference is not None, document.review_reference or now))

        logger.info("Documents due for review listed", due_count=len(due), interval_days=interval.days)

        return due

    def mark_reviewed(self, document_id: str, now: datetime | None = None) -> ReviewResult:
        """Set reviewed_at to now for one document and re-ingest only that document."""

        now = (now or datetime.now(timezone.utc)).replace(microsecond=0)

        with _manifest_lock:
            pdf_path = next((path for path in self._pdf_files() if document_id_from_source(path.name) == document_id), None)

            if pdf_path is None:
                raise NotFoundError(f"Document {document_id} not found.")

            manifest = load_manifest(self.manifest_path)
            info = manifest.get(pdf_path.name, DocumentInfo()).model_copy(update={"reviewed_at": now})
            manifest[pdf_path.name] = info

            # The manifest is written first: it is the source of truth, and a
            # failed re-indexing is repaired by any later ingestion.
            save_manifest(self.manifest_path, manifest)

            logger.info("Document review recorded", document_id=document_id, source=pdf_path.name, reviewed_at=now.isoformat())

            if self.vector_store_factory is None:
                raise RuntimeError("DocumentReviewService needs a vector store factory to re-ingest documents.")

            try:
                chunks = self.chunker.split(self.loader.load_file(pdf_path, info))
                self.vector_store_factory().replace_document(document_id, chunks)
            except Exception as exc:
                logger.exception("Re-ingestion after review failed", document_id=document_id, source=pdf_path.name)
                raise ExternalServiceError(
                    "The review was saved, but the document could not be re-indexed. "
                    "Retry the review or run: python -m scripts.ingest_documents"
                ) from exc

        return ReviewResult(document=self._record(pdf_path, info), chunk_count=len(chunks))

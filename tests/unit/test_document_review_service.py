import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from langchain_core.documents import Document
from src.rag.document_metadata import DocumentInfo, build_page_metadata, document_id_from_source, load_manifest
from src.services.document_review_service import DocumentReviewService
from src.services.exceptions import ExternalServiceError, NotFoundError

NOW = datetime(2026, 11, 12, 10, 0, 0, tzinfo=timezone.utc)


class FakeLoader:
    """Loads one page per PDF without parsing it, with the real metadata."""

    def load_file(self, pdf_path: Path, info: DocumentInfo) -> list[Document]:
        return [Document(page_content=f"Content of {pdf_path.name}. " * 5, metadata=build_page_metadata(pdf_path, {"page": 0}, info))]


class FakeVectorStore:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.replaced: dict[str, list[Document]] = {}

    def replace_document(self, document_id: str, chunks: list[Document]) -> None:
        if self.fail:
            raise RuntimeError("OpenAI is down")

        self.replaced[document_id] = chunks


def make_knowledge_base(tmp_path: Path, manifest: dict) -> Path:
    files = {
        "policies": ["warranty_policy.pdf", "security_policy.pdf"],
        "manuals": ["AIS-200_user_manual.pdf"],
        "faq": ["customer_faq.pdf"]
    }

    for category, names in files.items():
        (tmp_path / category).mkdir()

        for name in names:
            (tmp_path / category / name).write_bytes(b"%PDF-1.4")

    (tmp_path / "metadata.json").write_text(json.dumps(manifest), encoding="utf-8")

    return tmp_path


def make_service(directory: Path, vector_store: FakeVectorStore | None = None) -> DocumentReviewService:
    return DocumentReviewService(documents_directory=directory, vector_store_factory=lambda: vector_store or FakeVectorStore(), loader=FakeLoader())


MANIFEST = {
    "warranty_policy.pdf": {"date": "2025-01-01", "valid": True, "reviewed_at": "2025-11-11T09:00:00Z"},   # reviewed 366 days ago
    "security_policy.pdf": {"date": "2024-01-01", "valid": True, "reviewed_at": "2026-03-01"},             # reviewed recently
    "AIS-200_user_manual.pdf": {"date": "2025-06-01", "valid": True, "reviewed_at": None},                 # never reviewed, old date
    "customer_faq.pdf": {"date": "2026-01-25", "valid": True, "reviewed_at": None}                         # never reviewed, recent date
}


def test_due_documents_use_last_review_else_effective_date(tmp_path: Path) -> None:
    due = make_service(make_knowledge_base(tmp_path, MANIFEST)).documents_due_for_review(now=NOW)

    assert [document.source for document in due] == ["AIS-200_user_manual.pdf", "warranty_policy.pdf"]
    assert due[0].review_reference == datetime(2025, 6, 1, tzinfo=timezone.utc)
    assert due[0].days_since_reference == 529
    assert due[1].reviewed_at == datetime(2025, 11, 11, 9, tzinfo=timezone.utc)
    assert due[1].document_id == document_id_from_source("warranty_policy.pdf")


def test_exactly_one_year_is_not_yet_due(tmp_path: Path) -> None:
    manifest = {"warranty_policy.pdf": {"reviewed_at": "2025-11-12T10:00:00Z"}}

    due = make_service(make_knowledge_base(tmp_path, manifest)).documents_due_for_review(now=NOW)

    assert "warranty_policy.pdf" not in [document.source for document in due]


def test_documents_without_any_date_are_due_first_and_withdrawn_ones_are_skipped(tmp_path: Path) -> None:
    manifest = {**MANIFEST, "warranty_policy.pdf": {"valid": False}, "customer_faq.pdf": {}}

    due = make_service(make_knowledge_base(tmp_path, manifest)).documents_due_for_review(now=NOW)

    assert [document.source for document in due] == ["customer_faq.pdf", "AIS-200_user_manual.pdf"]
    assert due[0].review_reference is None
    assert due[0].days_since_reference is None


def test_custom_interval(tmp_path: Path) -> None:
    # customer_faq: effective 291 days ago; security_policy: reviewed 256 days ago.
    due = make_service(make_knowledge_base(tmp_path, MANIFEST)).documents_due_for_review(now=NOW, interval=timedelta(days=270))

    assert "customer_faq.pdf" in [document.source for document in due]
    assert "security_policy.pdf" not in [document.source for document in due]


def test_mark_reviewed_updates_manifest_and_reingests_only_that_document(tmp_path: Path) -> None:
    directory = make_knowledge_base(tmp_path, MANIFEST)
    vector_store = FakeVectorStore()
    document_id = document_id_from_source("AIS-200_user_manual.pdf")

    result = make_service(directory, vector_store).mark_reviewed(document_id, now=NOW.replace(microsecond=123))

    manifest = load_manifest(directory / "metadata.json")
    assert manifest["AIS-200_user_manual.pdf"].reviewed_at == NOW
    assert manifest["AIS-200_user_manual.pdf"].date.isoformat() == "2025-06-01"
    # The other entries are untouched.
    assert manifest["warranty_policy.pdf"].reviewed_at == datetime(2025, 11, 11, 9, tzinfo=timezone.utc)

    assert list(vector_store.replaced) == [document_id]
    chunks = vector_store.replaced[document_id]
    assert all(chunk.metadata["document_id"] == document_id for chunk in chunks)
    assert all(chunk.metadata["reviewed_at"] == "2026-11-12T10:00:00+00:00" for chunk in chunks)

    assert result.document.reviewed_at == NOW
    assert result.chunk_count == len(chunks)


def test_reviewed_document_is_no_longer_due(tmp_path: Path) -> None:
    service = make_service(make_knowledge_base(tmp_path, MANIFEST))

    service.mark_reviewed(document_id_from_source("warranty_policy.pdf"), now=NOW)

    assert "warranty_policy.pdf" not in [document.source for document in service.documents_due_for_review(now=NOW)]


def test_mark_reviewed_adds_a_missing_manifest_entry(tmp_path: Path) -> None:
    directory = make_knowledge_base(tmp_path, {})

    make_service(directory).mark_reviewed(document_id_from_source("customer_faq.pdf"), now=NOW)

    assert load_manifest(directory / "metadata.json")["customer_faq.pdf"] == DocumentInfo(reviewed_at=NOW)


def test_mark_reviewed_unknown_document(tmp_path: Path) -> None:
    with pytest.raises(NotFoundError):
        make_service(make_knowledge_base(tmp_path, MANIFEST)).mark_reviewed("not-a-document", now=NOW)


def test_failed_reingestion_keeps_the_saved_review(tmp_path: Path) -> None:
    directory = make_knowledge_base(tmp_path, MANIFEST)

    with pytest.raises(ExternalServiceError, match="review was saved"):
        make_service(directory, FakeVectorStore(fail=True)).mark_reviewed(document_id_from_source("warranty_policy.pdf"), now=NOW)

    assert load_manifest(directory / "metadata.json")["warranty_policy.pdf"].reviewed_at == NOW

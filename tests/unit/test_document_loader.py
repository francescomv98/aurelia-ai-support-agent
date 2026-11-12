import json
from pathlib import Path
import pytest
from langchain_core.documents import Document
from src.rag.document_loader import DocumentLoader
from src.rag.document_metadata import document_id_from_source

class FakePDFLoader:
    """Fake PDF loader used for unit testing."""

    def __init__(self, path: str) -> None:
        self.path = path

    def load(self) -> list[Document]:
        return [
            Document(
                page_content="Test document content.",
                metadata={"page": 0}
            ),
            Document(
                page_content="Second page content.",
                metadata={"page": 1}
            )
        ]


def test_load_directory(tmp_path: Path, monkeypatch) -> None:
    documents_directory = tmp_path / "documents"
    technical_directory = documents_directory / "technical"

    technical_directory.mkdir(parents=True)

    (technical_directory / "test.pdf").touch()
    (technical_directory / "ignored.txt").touch()

    monkeypatch.setattr("src.rag.document_loader.PyPDFLoader", FakePDFLoader)

    loader = DocumentLoader()

    documents = loader.load_directory(documents_directory)

    assert len(documents) == 2

    assert documents[0].metadata["source"] == "test.pdf"
    assert documents[0].metadata["category"] == "technical"
    assert documents[0].metadata["page"] == 0


def test_load_directory_without_pdfs(tmp_path: Path) -> None:
    loader = DocumentLoader()

    documents = loader.load_directory(tmp_path)

    assert documents == []


class NoisyPDFLoader(FakePDFLoader):
    """Returns the extra fields the real PyPDFLoader extracts from the PDF."""

    def load(self) -> list[Document]:
        return [Document(page_content="Content.", metadata={"page": 0, "total_pages": 1, "producer": "x", "creator": "y", "author": "z"})]


def make_knowledge_base(tmp_path: Path, manifest: dict | None) -> Path:
    manuals_directory = tmp_path / "manuals"
    manuals_directory.mkdir()
    (manuals_directory / "AIS-500_user_manual.pdf").touch()

    if manifest is not None:
        (tmp_path / "metadata.json").write_text(json.dumps(manifest), encoding="utf-8")

    return tmp_path


def test_load_directory_applies_manifest_and_drops_noise(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.rag.document_loader.PyPDFLoader", NoisyPDFLoader)
    directory = make_knowledge_base(tmp_path, {"AIS-500_user_manual.pdf": {"date": "2026-01-15", "valid": False, "reviewed_at": "2026-06-01"}})

    [document] = DocumentLoader().load_directory(directory)

    assert document.metadata == {
        "document_id": document_id_from_source("AIS-500_user_manual.pdf"),
        "source": "AIS-500_user_manual.pdf",
        "category": "manuals",
        "page": 0,
        "total_pages": 1,
        "product": "AIS-500",
        "doc_type": "user_manual",
        "title": "AIS-500 User Manual",
        "date": "2026-01-15",
        "valid": False,
        "reviewed_at": "2026-06-01T00:00:00+00:00"
    }


def test_document_missing_from_manifest_gets_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.rag.document_loader.PyPDFLoader", NoisyPDFLoader)
    directory = make_knowledge_base(tmp_path, {})

    [document] = DocumentLoader().load_directory(directory)

    assert document.metadata["valid"] is True
    assert document.metadata["date"] is None
    assert document.metadata["reviewed_at"] is None


def test_manifest_entry_for_unknown_file_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.rag.document_loader.PyPDFLoader", NoisyPDFLoader)
    directory = make_knowledge_base(tmp_path, {"AIS-500_user_manaul.pdf": {"valid": False}})

    with pytest.raises(ValueError, match="AIS-500_user_manaul.pdf"):
        DocumentLoader().load_directory(directory)
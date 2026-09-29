from pathlib import Path
from langchain_core.documents import Document
from src.rag.document_loader import DocumentLoader

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
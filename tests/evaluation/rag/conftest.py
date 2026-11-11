import pytest
from scripts.evaluate_rag import load_knowledge_base
from src.rag.chunker import DocumentChunker


@pytest.fixture(scope="session")
def knowledge_base():
    """The real PDFs, loaded and chunked offline exactly as the ingestion script does."""

    chunker = DocumentChunker()
    pdf_files, documents, chunks = load_knowledge_base(chunker)

    return {"chunker": chunker, "pdf_files": pdf_files, "documents": documents, "chunks": chunks}

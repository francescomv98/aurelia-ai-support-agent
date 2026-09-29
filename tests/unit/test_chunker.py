from langchain_core.documents import Document
from src.rag.chunker import DocumentChunker

def test_split_documents() -> None:
    documents = [
        Document(
            page_content="This is a test document. " * 100,
            metadata={
                "source": "test.pdf",
                "category": "test"
            }
        )
    ]

    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)

    chunks = chunker.split(documents)

    assert len(chunks) > 1
    assert all(len(chunk.page_content) <= 100 for chunk in chunks)


def test_split_empty_documents() -> None:
    chunker = DocumentChunker()

    chunks = chunker.split([])

    assert chunks == []


def test_chunk_metadata_is_preserved() -> None:
    documents = [
        Document(
            page_content="This is a test document.",
            metadata={
                "source": "test.pdf",
                "category": "technical",
                "page": 3
            }
        )
    ]

    chunker = DocumentChunker()

    chunks = chunker.split(documents)

    assert len(chunks) == 1
    assert chunks[0].metadata["source"] == "test.pdf"
    assert chunks[0].metadata["category"] == "technical"
    assert chunks[0].metadata["page"] == 3
import pytest
from langchain_core.documents import Document
from src.rag.chunker import DocumentChunker, document_title

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

def test_document_title_from_file_name() -> None:
    assert document_title("AIS-100_technical_specifications.pdf") == "AIS-100 Technical Specifications"
    assert document_title("customer_faq.pdf") == "Customer FAQ"


def test_chunks_start_with_document_title_and_respect_chunk_size() -> None:
    # A table chunk like this never names its product; the header gives it that context.
    documents = [Document(page_content="Approximate weight 1,850 kg. " * 40,
                          metadata={"source": "AIS-100_technical_specifications.pdf", "category": "technical", "page": 2})]

    chunks = DocumentChunker(chunk_size=200, chunk_overlap=20).split(documents)

    assert len(chunks) > 1
    assert all(chunk.page_content.startswith("[AIS-100 Technical Specifications]\n") for chunk in chunks)
    assert all(len(chunk.page_content) <= 200 for chunk in chunks)


def test_header_can_be_disabled() -> None:
    documents = [Document(page_content="Short text.", metadata={"source": "manual.pdf"})]

    chunks = DocumentChunker(add_document_header=False).split(documents)

    assert chunks[0].page_content == "Short text."


def test_document_without_source_gets_no_header() -> None:
    chunks = DocumentChunker().split([Document(page_content="Short text.", metadata={})])

    assert chunks[0].page_content == "Short text."


def test_chunk_size_too_small_for_header_is_rejected() -> None:
    documents = [Document(page_content="Text.", metadata={"source": "AIS-100_technical_specifications.pdf"})]

    with pytest.raises(ValueError, match="no room"):
        DocumentChunker(chunk_size=40, chunk_overlap=20).split(documents)


def test_table_split_by_a_page_break_ends_up_in_one_chunk() -> None:
    # Regression: the AIS-100 dimensions heading sat on page 1 and its values on page 2.
    pages = [
        Document(page_content="Intro text.\n3.1 Dimensions\nParameter Value", metadata={"source": "spec.pdf", "category": "technical", "page": 1}),
        Document(page_content="Length 2,200 mm\nApproximate weight 1,850 kg", metadata={"source": "spec.pdf", "category": "technical", "page": 2})
    ]

    chunks = DocumentChunker().split(pages)

    assert len(chunks) == 1
    assert "3.1 Dimensions" in chunks[0].page_content and "1,850 kg" in chunks[0].page_content
    assert chunks[0].metadata["page"] == 1


def test_chunks_keep_the_page_they_start_on() -> None:
    pages = [
        Document(page_content=f"Page {number} sentence. " * 30, metadata={"source": "manual.pdf", "category": "manuals", "page": number})
        for number in range(3)
    ]

    chunks = DocumentChunker(chunk_size=200, chunk_overlap=20).split(pages)

    for chunk in chunks:
        body = chunk.page_content.split("\n", 1)[1]
        # Overlap can start a chunk mid-phrase, so check that its opening text is on the assigned page.
        assert body[:20] in pages[chunk.metadata["page"]].page_content

    assert {chunk.metadata["page"] for chunk in chunks} == {0, 1, 2}


def test_different_files_are_never_merged() -> None:
    documents = [
        Document(page_content="Warranty is 24 months.", metadata={"source": "warranty_policy.pdf", "page": 0}),
        Document(page_content="Support hours are 08:00-18:00.", metadata={"source": "customer_faq.pdf", "page": 0})
    ]

    chunks = DocumentChunker().split(documents)

    assert [chunk.metadata["source"] for chunk in chunks] == ["warranty_policy.pdf", "customer_faq.pdf"]


def test_chunk_index_counts_from_zero_within_each_file() -> None:
    documents = [
        Document(page_content=f"Warranty sentence {number}. " * 20, metadata={"source": "warranty_policy.pdf", "page": number}) for number in range(2)
    ] + [
        Document(page_content="FAQ sentence. " * 20, metadata={"source": "customer_faq.pdf", "page": 0})
    ]

    chunks = DocumentChunker(chunk_size=200, chunk_overlap=20).split(documents)

    for source in ("warranty_policy.pdf", "customer_faq.pdf"):
        indexes = [chunk.metadata["chunk_index"] for chunk in chunks if chunk.metadata["source"] == source]
        assert indexes == list(range(len(indexes)))


def test_chunks_carry_the_page_metadata() -> None:
    page = Document(page_content="Content. " * 10, metadata={"source": "AIS-500_user_manual.pdf", "page": 0, "product": "AIS-500", "valid": False})

    [chunk] = DocumentChunker().split([page])

    assert chunk.metadata["product"] == "AIS-500"
    assert chunk.metadata["valid"] is False
    assert chunk.metadata["chunk_index"] == 0

from langchain_core.documents import Document
from src.rag.rag_service import RAGService

class FakeRetriever:
    """Fake retriever used for unit testing."""

    def retrieve(self, query: str) -> list[Document]:
        return [
            Document(
                page_content="AIS-200 has a maximum production speed of 80 units per minute.",
                metadata={
                    "source": "AIS-200_technical_specifications.pdf",
                    "page": 3,
                    "category": "technical"
                }
            ),
            Document(
                page_content="The AIS-200 preventive maintenance interval is 2000 operating hours.",
                metadata={
                    "source": "preventive_maintenance.pdf",
                    "page": 2,
                    "category": "maintenance"
                }
            )
        ]


def test_retrieve_context() -> None:
    retriever = FakeRetriever()
    service = RAGService(retriever=retriever)

    documents = service.retrieve_context("What is the AIS-200 maintenance interval?")

    assert len(documents) == 2


def test_retrieve_context_with_empty_query() -> None:
    retriever = FakeRetriever()
    service = RAGService(retriever=retriever)

    documents = service.retrieve_context("")

    assert documents == []


def test_build_context() -> None:
    retriever = FakeRetriever()
    service = RAGService(retriever=retriever)

    documents = retriever.retrieve("AIS-200")

    context = service.build_context(documents)

    assert "AIS-200_technical_specifications.pdf" in context
    assert "preventive_maintenance.pdf" in context
    assert "80 units per minute" in context
    assert "2000 operating hours" in context
    assert "technical" in context
    assert "maintenance" in context


def test_build_context_with_no_documents() -> None:
    retriever = FakeRetriever()
    service = RAGService(retriever=retriever)

    context = service.build_context([])

    assert context == ""


def test_build_context_header_shows_document_metadata() -> None:
    document = Document(
        page_content="Maximum speed: 80 units per minute.",
        metadata={
            "source": "AIS-200_technical_specifications.pdf",
            "title": "AIS-200 Technical Specifications",
            "page": 0,
            "category": "technical",
            "product": "AIS-200",
            "date": "2026-01-20",
            "reviewed_at": "2026-06-01"
        }
    )

    context = RAGService(retriever=FakeRetriever()).build_context([document])

    assert context.splitlines()[0] == (
        "[Source: AIS-200 Technical Specifications (AIS-200_technical_specifications.pdf) | Page: 1 | "
        "Category: technical | Product: AIS-200 | Effective date: 2026-01-20 | Last reviewed: 2026-06-01]"
    )


def test_build_context_header_for_general_never_reviewed_document() -> None:
    document = Document(
        page_content="Support hours are 08:00-18:00 CET.",
        metadata={"source": "customer_faq.pdf", "title": "Customer FAQ", "page": 2, "category": "faq",
                  "product": None, "date": "2026-01-25", "reviewed_at": None}
    )

    header = RAGService(retriever=FakeRetriever()).build_context([document]).splitlines()[0]

    assert header == ("[Source: Customer FAQ (customer_faq.pdf) | Page: 3 | Category: faq | "
                      "Effective date: 2026-01-25 | Last reviewed: never]")


def test_build_context_header_with_minimal_metadata() -> None:
    header = RAGService(retriever=FakeRetriever()).build_context([Document(page_content="text", metadata={})]).splitlines()[0]

    assert header == "[Source: unknown | Page: unknown | Category: unknown]"

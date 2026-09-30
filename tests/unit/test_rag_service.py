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

def test_extract_maintenance_interval() -> None:
    rag_service = RAGService(retriever=None)

    documents = [
        Document(
            page_content=(
                "AIS-100: preventive maintenance every 1,500 operating hours.\n"
                "AIS-200: preventive maintenance every 2,000 operating hours.\n"
                "AIS-500: preventive maintenance every 2,500 operating hours."
            ),
            metadata={}
        )
    ]

    result = rag_service.extract_maintenance_interval(documents=documents, model="AIS-200")

    assert result == 2000


def test_extract_maintenance_interval_not_found() -> None:
    rag_service = RAGService(retriever=None)

    documents = [
        Document(
            page_content="AIS-100: preventive maintenance every 1,500 operating hours.",
            metadata={}
        )
    ]

    result = rag_service.extract_maintenance_interval(documents=documents, model="AIS-200")

    assert result is None
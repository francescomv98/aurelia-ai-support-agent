from langchain_core.documents import Document
from src.rag.retriever import Retriever

class FakeVectorStore:
    """Fake vector store used for unit testing."""

    def similarity_search(self, query: str, k: int) -> list[Document]:
        return [
            Document(
                page_content="AIS-200 maximum production speed is 80 units per minute.",
                metadata={"source": "AIS-200_technical_specifications.pdf"}
            )
        ]


def test_retriever_returns_documents() -> None:
    vector_store = FakeVectorStore()
    retriever = Retriever(vector_store=vector_store, top_k=4)

    documents = retriever.retrieve("What is the maximum speed of AIS-200?")

    assert len(documents) == 1
    assert "80 units per minute" in documents[0].page_content


def test_retriever_returns_empty_list_for_empty_query() -> None:
    vector_store = FakeVectorStore()
    retriever = Retriever(vector_store=vector_store)

    documents = retriever.retrieve("")

    assert documents == []
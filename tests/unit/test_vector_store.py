from langchain_core.documents import Document
from src.rag.vector_store import VectorStore

class FakePGVector:
    """Fake PGVector implementation used for unit testing."""

    def __init__(self, embeddings, collection_name: str, connection: str, use_jsonb: bool) -> None:
        self.embeddings = embeddings
        self.collection_name = collection_name
        self.connection = connection
        self.use_jsonb = use_jsonb
        self.documents: list[Document] = []

    def add_documents(self, documents: list[Document]) -> None:
        self.documents.extend(documents)

    def similarity_search(self, query: str, k: int = 4) -> list[Document]:
        return self.documents[:k]


def test_vector_store_initialization(monkeypatch) -> None:
    monkeypatch.setattr("src.rag.vector_store.PGVector", FakePGVector)

    embeddings = object()

    vector_store = VectorStore(connection="test-connection", embeddings=embeddings)

    assert vector_store.store.collection_name == "aurelia_documents"
    assert vector_store.store.connection == "test-connection"
    assert vector_store.store.embeddings is embeddings
    assert vector_store.store.use_jsonb is True


def test_add_documents(monkeypatch) -> None:
    monkeypatch.setattr("src.rag.vector_store.PGVector", FakePGVector)

    vector_store = VectorStore(connection="test-connection", embeddings=object())

    documents = [
        Document(
            page_content="AIS-200 maximum speed is 80 units per minute.",
            metadata={"source": "test.pdf"}
        ),
        Document(
            page_content="Maintenance interval is 2000 hours.",
            metadata={"source": "maintenance.pdf"}
        )
    ]

    vector_store.add_documents(documents)

    assert len(vector_store.store.documents) == 2
    assert vector_store.store.documents[0].page_content.startswith("AIS-200")


def test_similarity_search(monkeypatch) -> None:
    monkeypatch.setattr("src.rag.vector_store.PGVector", FakePGVector)

    vector_store = VectorStore(connection="test-connection", embeddings=object())

    documents = [
        Document(page_content="Document 1"),
        Document(page_content="Document 2"),
        Document(page_content="Document 3")
    ]

    vector_store.add_documents(documents)

    results = vector_store.similarity_search(query="test query", k=2)

    assert len(results) == 2
    assert results[0].page_content == "Document 1"
    assert results[1].page_content == "Document 2"
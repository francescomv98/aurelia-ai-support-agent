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

    def similarity_search(self, query: str, k: int = 4, filter: dict | None = None) -> list[Document]:
        # Same semantics as PGVector's equality filter on metadata fields.
        matching = [document for document in self.documents if all(document.metadata.get(key) == value for key, value in (filter or {}).items())]

        return matching[:k]


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


def test_similarity_search_passes_metadata_filter(monkeypatch) -> None:
    monkeypatch.setattr("src.rag.vector_store.PGVector", FakePGVector)

    vector_store = VectorStore(connection="test-connection", embeddings=object())
    vector_store.add_documents([
        Document(page_content="Withdrawn policy", metadata={"valid": False}),
        Document(page_content="Current policy", metadata={"valid": True})
    ])

    results = vector_store.similarity_search(query="policy", k=4, filter={"valid": True})

    assert [document.page_content for document in results] == ["Current policy"]

def test_replace_document_adds_new_chunks_before_deleting_old_ones(monkeypatch) -> None:
    monkeypatch.setattr("src.rag.vector_store.PGVector", FakePGVector)

    vector_store = VectorStore(connection="test-connection", embeddings=object())
    calls: list[str] = []

    monkeypatch.setattr(vector_store, "chunk_ids", lambda document_id: ["old-1", "old-2"])
    monkeypatch.setattr(vector_store.store, "add_documents", lambda documents: calls.append(f"add {len(documents)}"), raising=False)
    monkeypatch.setattr(vector_store.store, "delete", lambda ids: calls.append(f"delete {ids}"), raising=False)

    vector_store.replace_document("doc-1", [Document(page_content="new chunk", metadata={"document_id": "doc-1"})])

    assert calls == ["add 1", "delete ['old-1', 'old-2']"]


def test_replace_document_keeps_old_chunks_when_adding_fails(monkeypatch) -> None:
    import pytest
    from sqlalchemy.exc import OperationalError
    from src.services.exceptions import DatabaseError

    monkeypatch.setattr("src.rag.vector_store.PGVector", FakePGVector)

    vector_store = VectorStore(connection="test-connection", embeddings=object())
    deleted: list[list[str]] = []

    def failing_add(documents):
        raise OperationalError("INSERT", {}, Exception("connection lost"))

    monkeypatch.setattr(vector_store, "chunk_ids", lambda document_id: ["old-1"])
    monkeypatch.setattr(vector_store.store, "add_documents", failing_add)
    monkeypatch.setattr(vector_store.store, "delete", lambda ids: deleted.append(ids), raising=False)

    with pytest.raises(DatabaseError):
        vector_store.replace_document("doc-1", [Document(page_content="new chunk")])

    assert deleted == []


def test_similarity_search_reports_embedding_failure_as_external_service_error(monkeypatch) -> None:
    import httpx
    import openai
    import pytest
    from src.services.exceptions import ExternalServiceError

    monkeypatch.setattr("src.rag.vector_store.PGVector", FakePGVector)

    vector_store = VectorStore(connection="test-connection", embeddings=object())

    def failing_search(query, k, filter=None):
        raise openai.APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/embeddings"))

    monkeypatch.setattr(vector_store.store, "similarity_search", failing_search)

    with pytest.raises(ExternalServiceError):
        vector_store.similarity_search(query="warranty")

from langchain_core.documents import Document
from src.rag.retriever import ONLY_VALID_DOCUMENTS, Retriever, build_filter

class FakeVectorStore:
    """Fake vector store used for unit testing."""

    def __init__(self) -> None:
        self.filter = None

    def similarity_search(self, query: str, k: int, filter: dict | None = None) -> list[Document]:
        self.filter = filter

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


def test_retriever_only_searches_valid_documents() -> None:
    vector_store = FakeVectorStore()

    Retriever(vector_store=vector_store).retrieve("What does error code E-204 mean?")

    assert vector_store.filter == {"valid": True}


def test_retriever_restricts_to_the_named_product_and_general_documents() -> None:
    vector_store = FakeVectorStore()

    Retriever(vector_store=vector_store).retrieve("What is the maximum speed of AIS-200?")

    assert vector_store.filter == {
        "$and": [{"valid": True}, {"$or": [{"product": "AIS-200"}, {"product": None}]}]
    }


def test_retriever_without_product_filter_only_filters_validity() -> None:
    vector_store = FakeVectorStore()

    Retriever(vector_store=vector_store, product_filter=False).retrieve("What is the maximum speed of AIS-200?")

    assert vector_store.filter == ONLY_VALID_DOCUMENTS


def test_filter_keeps_every_named_product() -> None:
    metadata_filter = build_filter("Compare the AIS-100 and the AIS-500")

    assert metadata_filter["$and"][1] == {"$or": [{"product": "AIS-100"}, {"product": "AIS-500"}, {"product": None}]}


def test_retriever_returns_empty_list_for_empty_query() -> None:
    vector_store = FakeVectorStore()
    retriever = Retriever(vector_store=vector_store)

    documents = retriever.retrieve("")

    assert documents == []


def test_product_filter_compiles_to_pgvector_sql() -> None:
    """The filter must be one langchain-postgres can translate (no database needed: the SQL is only compiled).

    Uses PGVector internals on purpose: a library upgrade that stops supporting
    $and/$or or a null equality should fail here, not silently in production.
    """

    from langchain_postgres import PGVector
    from langchain_postgres.vectorstores import _get_embedding_collection_store
    from sqlalchemy.dialects import postgresql

    store = PGVector.__new__(PGVector)
    store.EmbeddingStore, store.CollectionStore = _get_embedding_collection_store()
    store.use_jsonb = True

    clause = store._create_filter_clause(build_filter("AIS-200 speed"))
    params = clause.compile(dialect=postgresql.dialect()).params

    assert sorted(params.values(), key=str) == sorted(
        ["$.valid == $value", {"value": True}, "$.product == $value", {"value": "AIS-200"}, "$.product == $value", {"value": None}],
        key=str
    )

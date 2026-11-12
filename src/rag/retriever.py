from typing import Any
from langchain_core.documents import Document
from src.app_logging.logger import logger
from src.rag.document_metadata import products_mentioned
from src.rag.vector_store import VectorStore

# Documents an owner has invalidated (valid: false in data/documents/metadata.json) are never retrieved.
ONLY_VALID_DOCUMENTS = {"valid": True}


def build_filter(query: str, product_filter: bool = True) -> dict[str, Any]:
    """Metadata filter for a query.

    Always restricted to valid documents. When the query names one or more
    products (e.g. "AIS-200") and product_filter is on, it is also restricted
    to the documents of those products plus the general documents (product
    null: FAQ, maintenance, policies), so the near-identical manuals and
    specifications of the other models cannot crowd out the right ones.
    """

    products = products_mentioned(query) if product_filter else []

    if not products:
        return ONLY_VALID_DOCUMENTS

    return {
        "$and": [
            ONLY_VALID_DOCUMENTS,
            {"$or": [*({"product": product} for product in products), {"product": None}]}
        ]
    }


class Retriever:
    """Retrieve relevant documents from the vector store."""

    def __init__(self, vector_store: VectorStore, top_k: int = 4, product_filter: bool = True) -> None:
        self.vector_store = vector_store
        self.top_k = top_k
        self.product_filter = product_filter

        logger.info("Retriever initialized", top_k=top_k, product_filter=product_filter)

    def retrieve(self, query: str) -> list[Document]:
        """Retrieve the most relevant documents for a query."""

        if not query.strip():
            logger.warning("Empty retrieval query")
            return []

        metadata_filter = build_filter(query, self.product_filter)

        logger.info("Retrieving relevant documents", top_k=self.top_k, filter=metadata_filter)

        try:
            documents = self.vector_store.similarity_search(query=query, k=self.top_k, filter=metadata_filter)

            logger.info("Documents retrieved successfully", result_count=len(documents))

            return documents

        except Exception:
            logger.exception("Document retrieval failed")
            raise

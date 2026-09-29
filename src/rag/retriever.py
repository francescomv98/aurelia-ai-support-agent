from langchain_core.documents import Document
from src.logging.logger import logger
from src.rag.vector_store import VectorStore

class Retriever:
    """Retrieve relevant documents from the vector store."""

    def __init__(self, vector_store: VectorStore, top_k: int = 4) -> None:
        self.vector_store = vector_store
        self.top_k = top_k

        logger.info("Retriever initialized", top_k=top_k)

    def retrieve(self, query: str) -> list[Document]:
        """Retrieve the most relevant documents for a query."""

        if not query.strip():
            logger.warning("Empty retrieval query")
            return []

        logger.info("Retrieving relevant documents", top_k=self.top_k)

        try:
            documents = self.vector_store.similarity_search(query=query, k=self.top_k)

            logger.info("Documents retrieved successfully", result_count=len(documents))

            return documents

        except Exception:
            logger.exception("Document retrieval failed")
            raise
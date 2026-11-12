from langchain_core.documents import Document
from src.app_logging.logger import logger
from src.rag.retriever import Retriever

class RAGService:
    """Handle document retrieval and context preparation."""

    def __init__(self, retriever: Retriever) -> None:
        self.retriever = retriever

        logger.info("RAG service initialized")

    def retrieve_context(self, query: str) -> list[Document]:
        """Retrieve relevant documents for a query."""

        if not query.strip():
            logger.warning("Empty RAG query")
            return []

        logger.info("Retrieving context for RAG query")

        try:
            documents = self.retriever.retrieve(query)

            logger.info("RAG context retrieved", document_count=len(documents))

            return documents

        except Exception:
            logger.exception("Failed to retrieve RAG context")
            raise


    @staticmethod
    def _header(metadata: dict) -> str:
        """Describe a chunk's origin: "[Source: AIS-200 User Manual (AIS-200_user_manual.pdf) | Page: 3 | ...]".

        Pages are shown from 1 (PyPDF counts from 0) so they match what the
        customer sees in the PDF. Dates let the model tell how current a
        document is; fields missing from older chunks are left out.
        """

        source = metadata.get("source", "unknown")
        title = metadata.get("title")
        page = metadata.get("page")

        parts = [
            f"Source: {title} ({source})" if title else f"Source: {source}",
            f"Page: {page + 1}" if isinstance(page, int) else "Page: unknown",
            f"Category: {metadata.get('category', 'unknown')}"
        ]

        if metadata.get("product"):
            parts.append(f"Product: {metadata['product']}")

        if metadata.get("date"):
            parts.append(f"Effective date: {metadata['date']}")

        if "reviewed_at" in metadata:
            parts.append(f"Last reviewed: {metadata['reviewed_at'] or 'never'}")

        return f"[{' | '.join(parts)}]"

    def build_context(self, documents: list[Document]) -> str:
        """Build a textual context from retrieved documents."""

        if not documents:
            logger.warning("No documents available to build RAG context")
            return ""

        context_parts: list[str] = []

        for document in documents:
            context_parts.append(f"{self._header(document.metadata)}\n{document.page_content}")

        context = "\n\n".join(context_parts)

        logger.info("RAG context built", document_count=len(documents), context_length=len(context))

        return context
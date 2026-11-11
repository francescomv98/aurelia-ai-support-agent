from langchain_core.documents import Document
from src.app_logging.logger import logger
from src.rag.retriever import Retriever
import re

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


    def extract_maintenance_interval(self, documents: list[Document], model: str) -> int | None:
        """Extract the maintenance interval for a machine model."""

        pattern = rf"{re.escape(model)}.*?(\d[\d,]*)\s*(?:operating hours|hours)"

        for document in documents:
            match = re.search(pattern, document.page_content, flags=re.IGNORECASE | re.DOTALL)

            if match:
                interval = int(match.group(1).replace(",", ""))

                logger.info("Maintenance interval extracted", model=model, maintenance_interval=interval)

                return interval

        logger.warning("Maintenance interval not found in RAG documents", model=model)

        return None
    

    def build_context(self, documents: list[Document]) -> str:
        """Build a textual context from retrieved documents."""

        if not documents:
            logger.warning("No documents available to build RAG context")
            return ""

        context_parts: list[str] = []

        for document in documents:
            source = document.metadata.get("source", "unknown")
            page = document.metadata.get("page", "unknown")
            category = document.metadata.get("category", "unknown")

            context_parts.append(
                f"[Source: {source} | Page: {page} | Category: {category}]\n"
                f"{document.page_content}"
            )

        context = "\n\n".join(context_parts)

        logger.info("RAG context built", document_count=len(documents), context_length=len(context))

        return context
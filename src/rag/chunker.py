from src.logging.logger import logger
from langchain_core.documents import Document

class DocumentChunker:
    """Split documents into smaller chunks."""

    def split(self, documents: list[Document]) -> list[Document]:
        """Split documents into chunks."""

        logger.info(
            "Splitting documents into chunks",
            document_count=len(documents),
        )

        chunks = self.splitter.split_documents(documents)

        logger.info(
            "Documents split successfully",
            document_count=len(documents),
            chunk_count=len(chunks),
        )

        return chunks
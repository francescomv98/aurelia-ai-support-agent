from src.app_logging.logger import logger
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class DocumentChunker:
    """Split documents into smaller chunks."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150) -> None:
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        logger.info("Document chunker initialized", chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def split(self, documents: list[Document]) -> list[Document]:
        """Split documents into chunks."""

        logger.info("Splitting documents into chunks", document_count=len(documents))

        chunks = self.splitter.split_documents(documents)

        logger.info("Documents split successfully", document_count=len(documents), chunk_count=len(chunks))

        return chunks
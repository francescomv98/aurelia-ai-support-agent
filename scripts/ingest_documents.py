import os
from pathlib import Path
from dotenv import load_dotenv
from src.app_logging.logger import configure_logging, logger
from src.rag.chunker import DocumentChunker
from src.rag.document_loader import DocumentLoader
from src.rag.embedding import create_embeddings
from src.rag.vector_store import VectorStore

def main() -> None:
    """Ingest knowledge base documents into the vector store."""

    configure_logging()
    load_dotenv()

    logger.info("Starting document ingestion")

    documents_path = Path("data/documents")

    if not documents_path.exists():
        logger.error("Documents directory not found", directory=str(documents_path))
        raise FileNotFoundError(f"Documents directory not found: {documents_path}")

    connection = os.getenv("DATABASE_URL")

    if not connection:
        logger.error("Database connection is not configured")
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    try:
        loader = DocumentLoader()
        chunker = DocumentChunker()
        embeddings = create_embeddings()

        vector_store = VectorStore(connection=connection, embeddings=embeddings)

        documents = loader.load_directory(documents_path)
        chunks = chunker.split(documents)

        # Rebuild the collection from scratch: re-running the script must not
        # duplicate chunks, and removed/changed documents must not linger.
        vector_store.reset()
        vector_store.add_documents(chunks)

        logger.info("Document ingestion completed successfully", document_count=len(documents), chunk_count=len(chunks))

    except Exception:
        logger.exception("Document ingestion failed")
        raise


if __name__ == "__main__":
    main()
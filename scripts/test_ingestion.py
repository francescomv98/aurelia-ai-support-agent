from pathlib import Path
from src.logging.logger import configure_logging, logger
from src.rag.chunker import DocumentChunker
from src.rag.document_loader import DocumentLoader

def main() -> None:
    """Test document ingestion and chunking."""

    configure_logging()

    documents_path = Path("data/documents")

    loader = DocumentLoader()
    chunker = DocumentChunker()

    documents = loader.load_directory(documents_path)

    chunks = chunker.split(documents)

    logger.info("Ingestion and chunking test completed", document_count=len(documents), chunk_count=len(chunks))

    if chunks:
        first_chunk = chunks[0]

        logger.info("First chunk sample", source=first_chunk.metadata.get("source"), category=first_chunk.metadata.get("category"),
            page=first_chunk.metadata.get("page"), content_length=len(first_chunk.page_content), content_preview=first_chunk.page_content[:200])


if __name__ == "__main__":
    main()
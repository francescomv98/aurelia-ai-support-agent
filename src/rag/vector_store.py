from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from src.app_logging.logger import logger
from sqlalchemy.exc import SQLAlchemyError
from src.services.exceptions import DatabaseError

class VectorStore:
    """Manage the PostgreSQL vector store."""

    def __init__(self, connection: str, embeddings: OpenAIEmbeddings, collection_name: str = "aurelia_documents") -> None:
        self.store = PGVector(embeddings=embeddings, collection_name=collection_name, connection=connection, use_jsonb=True)

        logger.info("Vector store initialized", collection=collection_name)

    def reset(self) -> None:
        """Drop and recreate the collection so a re-ingestion does not duplicate chunks."""

        logger.info("Resetting vector store collection")

        self.store.delete_collection()
        self.store.create_collection()

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the vector store."""

        logger.info("Adding documents to vector store", document_count=len(documents))

        try:
            self.store.add_documents(documents)

            logger.info("Documents added to vector store", document_count=len(documents))

        except Exception:
            logger.exception("Failed to add documents to vector store")
            raise

    def similarity_search(self, query: str, k: int = 4) -> list[Document]:
        """Retrieve the most relevant documents."""

        logger.info("Running vector similarity search", top_k=k)

        try:
            documents = self.store.similarity_search(query, k=k)

            logger.info("Vector similarity search completed", result_count=len(documents))

            return documents
        
        except SQLAlchemyError as exc:
            logger.exception("Vector similarity search failed")
            raise DatabaseError("Vector store operation failed.") from exc
        except Exception:
            logger.exception("Vector similarity search failed")
            raise
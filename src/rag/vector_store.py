from typing import Any
import openai
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from src.app_logging.logger import logger
from sqlalchemy.exc import SQLAlchemyError
from src.services.exceptions import DatabaseError, ExternalServiceError

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

    def chunk_ids(self, document_id: str) -> list[str]:
        """Ids of the stored chunks of one document (matched on the document_id metadata)."""

        # PGVector has no public "find by metadata" method, hence its session and models.
        with self.store._make_sync_session() as session:
            collection = self.store.get_collection(session)

            if collection is None:
                return []

            embedding = self.store.EmbeddingStore
            rows = session.query(embedding.id).filter(
                embedding.collection_id == collection.uuid,
                embedding.cmetadata["document_id"].astext == document_id
            ).all()

            return [row.id for row in rows]

    def replace_document(self, document_id: str, chunks: list[Document]) -> None:
        """Replace the stored chunks of one document with new ones.

        The new chunks are added before the old ones are deleted, so the
        document never disappears from search; if the embedding call fails,
        the old chunks are left untouched.
        """

        logger.info("Replacing document chunks", document_id=document_id, chunk_count=len(chunks))

        try:
            old_ids = self.chunk_ids(document_id)

            self.store.add_documents(chunks)

            if old_ids:
                self.store.delete(ids=old_ids)

            logger.info("Document chunks replaced", document_id=document_id, removed=len(old_ids), added=len(chunks))

        except SQLAlchemyError as exc:
            logger.exception("Failed to replace document chunks", document_id=document_id)
            raise DatabaseError("Vector store operation failed.") from exc

    def similarity_search(self, query: str, k: int = 4, filter: dict[str, Any] | None = None) -> list[Document]:
        """Retrieve the most relevant documents, optionally restricted by a metadata filter such as {"valid": True}."""

        logger.info("Running vector similarity search", top_k=k, filter=filter)

        try:
            documents = self.store.similarity_search(query, k=k, filter=filter)

            logger.info("Vector similarity search completed", result_count=len(documents))

            return documents
        
        except SQLAlchemyError as exc:
            logger.exception("Vector similarity search failed")
            raise DatabaseError("Vector store operation failed.") from exc
        except openai.APIError as exc:
            # The query is embedded by OpenAI before the search; the SDK has already retried.
            logger.exception("Query embedding failed")
            raise ExternalServiceError("The embedding service is unavailable.") from exc
        except Exception:
            logger.exception("Vector similarity search failed")
            raise
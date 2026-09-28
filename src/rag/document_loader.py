from src.logging.logger import logger
from pathlib import Path
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader

class DocumentLoader:
    """Load PDF documents from the knowledge base."""

    def load_directory(self, directory: Path) -> list[Document]:
        """Load all PDF documents from a directory recursively."""

        documents: list[Document] = []

        pdf_files = sorted(directory.rglob("*.pdf"))

        logger.info(
            "Loading knowledge base documents",
            directory=str(directory),
            pdf_count=len(pdf_files),
        )

        for pdf_path in pdf_files:
            try:
                loader = PyPDFLoader(str(pdf_path))
                loaded_documents = loader.load()

                for document in loaded_documents:
                    document.metadata["source"] = pdf_path.name
                    document.metadata["category"] = pdf_path.parent.name

                documents.extend(loaded_documents)

                logger.info(
                    "Document loaded",
                    source=pdf_path.name,
                    category=pdf_path.parent.name,
                    page_count=len(loaded_documents),
                )

            except Exception:
                logger.exception(
                    "Failed to load document",
                    source=pdf_path.name,
                )
                raise

        logger.info(
            "Knowledge base documents loaded",
            pdf_count=len(pdf_files),
            document_count=len(documents),
        )

        return documents
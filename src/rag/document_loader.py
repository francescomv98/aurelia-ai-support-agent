from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from src.app_logging.logger import logger
from src.rag.document_metadata import MANIFEST_FILE_NAME, DocumentInfo, build_page_metadata, load_manifest

class DocumentLoader:
    """Load PDF documents from the knowledge base."""

    def load_directory(self, directory: Path) -> list[Document]:
        """Load all PDF documents from a directory recursively.

        Owner-managed metadata (date, valid, reviewed_at) comes from the
        metadata.json manifest at the root of the directory.
        """

        documents: list[Document] = []

        pdf_files = sorted(directory.rglob("*.pdf"))
        manifest = load_manifest(directory / MANIFEST_FILE_NAME)

        unknown_entries = sorted(set(manifest) - {pdf_path.name for pdf_path in pdf_files})

        if unknown_entries:
            # Most likely a typo or a renamed file: the entry would silently never apply.
            raise ValueError(f"{MANIFEST_FILE_NAME} lists files that do not exist: {', '.join(unknown_entries)}")

        logger.info("Loading knowledge base documents", directory=str(directory), pdf_count=len(pdf_files))

        for pdf_path in pdf_files:
            info = manifest.get(pdf_path.name)

            if info is None:
                logger.warning("Document missing from metadata manifest, using defaults", source=pdf_path.name)
                info = DocumentInfo()

            documents.extend(self.load_file(pdf_path, info))

        logger.info("Knowledge base documents loaded", pdf_count=len(pdf_files), document_count=len(documents))

        return documents

    def load_file(self, pdf_path: Path, info: DocumentInfo) -> list[Document]:
        """Load the pages of one PDF with their metadata (used alone to re-ingest a single document)."""

        try:
            loaded_documents = PyPDFLoader(str(pdf_path)).load()

            for document in loaded_documents:
                document.metadata = build_page_metadata(pdf_path, document.metadata, info)

            logger.info("Document loaded", source=pdf_path.name, category=pdf_path.parent.name, page_count=len(loaded_documents), valid=info.valid)

            return loaded_documents

        except Exception:
            logger.exception("Failed to load document", source=pdf_path.name)
            raise

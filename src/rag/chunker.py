from bisect import bisect_right
from itertools import groupby
from pathlib import Path
from src.app_logging.logger import logger
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

ACRONYMS = {"faq": "FAQ"}


def document_title(source: str) -> str:
    """Turn a file name into a readable title: "AIS-100_technical_specifications.pdf" -> "AIS-100 Technical Specifications"."""

    words = Path(source).stem.replace("_", " ").split()

    return " ".join(
        ACRONYMS.get(word.lower(), word if any(character.isupper() for character in word) else word.capitalize())
        for word in words
    )


class DocumentChunker:
    """Split documents into smaller chunks.

    Each chunk starts with the title of its document, for example
    "[AIS-100 Technical Specifications]". Without it, a chunk such as a table of
    dimensions never names the product it describes, and the retrieval
    evaluation showed such chunks ranking below unrelated ones. The header
    counts towards chunk_size, so no chunk exceeds it.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100, add_document_header: bool = True) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.add_document_header = add_document_header
        self._splitters: dict[int, RecursiveCharacterTextSplitter] = {}

        logger.info("Document chunker initialized", chunk_size=chunk_size, chunk_overlap=chunk_overlap, add_document_header=add_document_header)

    def _header(self, document: Document) -> str:
        source = document.metadata.get("source")

        if not self.add_document_header or not source:
            return ""

        return f"[{document_title(source)}]\n"

    def _splitter(self, body_size: int) -> RecursiveCharacterTextSplitter:
        if body_size <= self.chunk_overlap:
            raise ValueError(f"chunk_size {self.chunk_size} leaves no room for content after the document header.")

        if body_size not in self._splitters:
            self._splitters[body_size] = RecursiveCharacterTextSplitter(chunk_size=body_size, chunk_overlap=self.chunk_overlap, add_start_index=True)

        return self._splitters[body_size]

    def _split_file(self, pages: list[Document]) -> list[Document]:
        """Split the consecutive pages of one file as a single text.

        Splitting page by page cuts tables in two at every page break: the
        evaluation found the AIS-100 dimensions heading on one page and its
        values (weight, size) on the next, in chunks that never met. Each chunk
        keeps the metadata of the page it starts on.
        """

        header = self._header(pages[0])
        page_starts: list[int] = []
        texts: list[str] = []
        offset = 0

        for page in pages:
            page_starts.append(offset)
            texts.append(page.page_content)
            offset += len(page.page_content) + 1  # the "\n" joining pages

        merged = Document(page_content="\n".join(texts), metadata=dict(pages[0].metadata))
        chunks: list[Document] = []

        for chunk in self._splitter(self.chunk_size - len(header)).split_documents([merged]):
            start = chunk.metadata.pop("start_index")
            # The splitter reports -1 when it cannot locate the chunk; fall back to the first page.
            start_page = pages[max(bisect_right(page_starts, start) - 1, 0)]

            chunks.append(Document(page_content=header + chunk.page_content, metadata=dict(start_page.metadata)))

        return chunks

    def split(self, documents: list[Document]) -> list[Document]:
        """Split documents into chunks, joining consecutive pages of the same file."""

        logger.info("Splitting documents into chunks", document_count=len(documents))

        chunks: list[Document] = []

        for source, group in groupby(documents, key=lambda document: document.metadata.get("source")):
            pages = list(group)

            if source is None:
                # Without a source there is no way to tell which pages belong together.
                for page in pages:
                    chunks.extend(self._split_file([page]))
            else:
                chunks.extend(self._split_file(pages))

        logger.info("Documents split successfully", document_count=len(documents), chunk_count=len(chunks))

        return chunks

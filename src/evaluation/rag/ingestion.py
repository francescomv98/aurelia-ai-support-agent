"""Ingestion evaluation: did the PDFs turn into complete, well-formed chunks?

Runs offline on the same loader and chunker that scripts/ingest_documents.py
uses, so it needs no API key. The optional vector-store check compares the
chunks (text and metadata) with what is actually stored in the database.
"""

import json
from pathlib import Path
from typing import Any
from langchain_core.documents import Document
from src.evaluation.rag.common import Check, StageReport, contains_phrase, ratio

# product, date and reviewed_at may legitimately be empty (general documents, never reviewed).
REQUIRED_METADATA = ("document_id", "source", "category", "page", "doc_type", "title", "chunk_index", "valid")
MIN_CHUNK_CHARS = 50


def _page_label(document: Document) -> str:
    return f"{document.metadata.get('source', 'unknown')} page {document.metadata.get('page', '?')}"


def evaluate_ingestion_case(case: dict[str, Any], chunks: list[Document]) -> dict[str, Any]:
    """Check that a known fact survived PDF extraction and chunking intact.

    The fact must sit inside a single chunk from the expected source: a fact
    split across two chunks, or lost by the PDF parser, cannot be retrieved.
    """

    matching_chunks = [
        chunk for chunk in chunks
        if chunk.metadata.get("source") == case["source"] and contains_phrase(chunk.page_content, case["fact"])
    ]

    return {
        "id": case["id"],
        "fact": case["fact"],
        "source": case["source"],
        "passed": bool(matching_chunks),
        "matching_chunks": len(matching_chunks)
    }


def _chunk_key(chunk: Document) -> tuple[str, str]:
    return chunk.page_content, json.dumps(chunk.metadata, sort_keys=True, default=str)


def vector_store_check(stored_chunks: list[Document], chunks: list[Document]) -> Check:
    """Check that the vector store holds exactly the chunks the current ingestion code produces.

    Text and metadata are both compared. A store left over from an older
    chunker still answers queries, and one with outdated metadata ignores a
    document an owner has just invalidated, so without this check the
    retrieval metrics silently measure an out-of-date index.
    """

    expected = sorted(_chunk_key(chunk) for chunk in chunks)
    stored = sorted(_chunk_key(chunk) for chunk in stored_chunks)
    matches = stored == expected

    details = [] if matches else [
        f"vector store holds {len(stored)} chunks, current ingestion produces {len(expected)}; "
        f"{len(set(expected) - set(stored))} current chunks are missing from the store or have different metadata. "
        "Re-run: python -m scripts.ingest_documents"
    ]

    return Check("vector_store_up_to_date", 1.0 if matches else 0.0, 1.0, details=details)


def evaluate_ingestion(pdf_files: list[Path], documents: list[Document], chunks: list[Document], cases: list[dict[str, Any]],
                       chunk_size: int, stored_chunks: list[Document] | None = None) -> StageReport:
    """Evaluate loading, chunking and (optionally) storage of the knowledge base."""

    loaded_sources = {document.metadata.get("source") for document in documents}
    missing_files = [pdf.name for pdf in pdf_files if pdf.name not in loaded_sources]

    empty_pages = [_page_label(document) for document in documents if not document.page_content.strip()]

    incomplete_metadata = [
        _page_label(chunk) for chunk in chunks
        if any(chunk.metadata.get(key) in (None, "") for key in REQUIRED_METADATA)
    ]

    oversized_chunks = [f"{_page_label(chunk)} ({len(chunk.page_content)} chars)" for chunk in chunks if len(chunk.page_content) > chunk_size]

    tiny_chunks = [f"{_page_label(chunk)} ({len(chunk.page_content.strip())} chars)" for chunk in chunks if len(chunk.page_content.strip()) < MIN_CHUNK_CHARS]

    seen_contents: set[str] = set()
    duplicate_chunks: list[str] = []

    for chunk in chunks:
        content = chunk.page_content.strip()

        if content in seen_contents:
            duplicate_chunks.append(_page_label(chunk))

        seen_contents.add(content)

    case_results = [evaluate_ingestion_case(case, chunks) for case in cases]
    missing_facts = [f"{result['id']}: '{result['fact']}' not found in {result['source']}" for result in case_results if not result["passed"]]

    checks = [
        Check("pdf_files_loaded", ratio(len(pdf_files) - len(missing_files), len(pdf_files)), 1.0, details=missing_files),
        # Image-only pages (scanned tables, diagrams) lose their content; reported, not fatal.
        Check("pages_with_text", ratio(len(documents) - len(empty_pages), len(documents)), 1.0, level="warning", details=empty_pages),
        Check("chunk_metadata_complete", ratio(len(chunks) - len(incomplete_metadata), len(chunks)), 1.0, details=incomplete_metadata),
        Check("chunks_within_size_limit", ratio(len(chunks) - len(oversized_chunks), len(chunks)), 1.0, details=oversized_chunks),
        Check("chunks_not_tiny", ratio(len(chunks) - len(tiny_chunks), len(chunks)), 0.95, level="warning", details=tiny_chunks),
        Check("unique_chunks", ratio(len(chunks) - len(duplicate_chunks), len(chunks)), 1.0, details=duplicate_chunks),
        Check("fact_coverage", ratio(sum(result["passed"] for result in case_results), len(case_results)), 1.0, details=missing_facts)
    ]

    if stored_chunks is not None:
        checks.append(vector_store_check(stored_chunks, chunks))

    return StageReport(stage="ingestion", checks=checks, cases=case_results)

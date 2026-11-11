from pathlib import Path
from langchain_core.documents import Document
from scripts.evaluate_rag import load_cases
from src.evaluation.rag.ingestion import evaluate_ingestion


def make_document(content: str, source: str = "manual.pdf", page: int = 0, category: str = "manuals") -> Document:
    return Document(page_content=content, metadata={"source": source, "category": category, "page": page})


def check(report, name: str):
    return next(check for check in report.checks if check.name == name)


CHUNK = "The AIS-200 requires preventive maintenance every 2,000 operating hours of production use."


def test_clean_ingestion_passes() -> None:
    documents = [make_document(CHUNK)]

    report = evaluate_ingestion(pdf_files=[Path("manual.pdf")], documents=documents, chunks=documents,
                                cases=[{"id": "ING-1", "source": "manual.pdf", "fact": "2,000 operating hours"}], chunk_size=1000)

    assert report.passed
    assert all(item.passed for item in report.checks)


def test_pdf_without_pages_fails() -> None:
    report = evaluate_ingestion(pdf_files=[Path("manual.pdf"), Path("missing.pdf")], documents=[make_document(CHUNK)],
                                chunks=[make_document(CHUNK)], cases=[], chunk_size=1000)

    assert not report.passed
    assert check(report, "pdf_files_loaded").details == ["missing.pdf"]


def test_empty_page_is_a_warning_only() -> None:
    documents = [make_document(CHUNK), make_document("   ", page=8)]

    report = evaluate_ingestion(pdf_files=[Path("manual.pdf")], documents=documents, chunks=[documents[0]], cases=[], chunk_size=1000)

    assert report.passed
    assert check(report, "pages_with_text").status == "WARN"
    assert check(report, "pages_with_text").details == ["manual.pdf page 8"]


def test_missing_metadata_fails() -> None:
    chunk = Document(page_content=CHUNK, metadata={"source": "manual.pdf", "page": 0})

    report = evaluate_ingestion(pdf_files=[Path("manual.pdf")], documents=[chunk], chunks=[chunk], cases=[], chunk_size=1000)

    assert check(report, "chunk_metadata_complete").status == "FAIL"


def test_oversized_and_duplicate_chunks_fail() -> None:
    chunks = [make_document("x" * 1200), make_document(CHUNK), make_document(CHUNK, page=1)]

    report = evaluate_ingestion(pdf_files=[Path("manual.pdf")], documents=chunks, chunks=chunks, cases=[], chunk_size=1000)

    assert check(report, "chunks_within_size_limit").status == "FAIL"
    assert check(report, "unique_chunks").details == ["manual.pdf page 1"]


def test_fact_split_across_chunks_is_not_covered() -> None:
    # The splitter cut the fact in half: neither chunk holds it whole, so retrieval cannot find it.
    chunks = [make_document("Preventive maintenance every 2,000"), make_document("operating hours is mandatory.", page=1)]

    report = evaluate_ingestion(pdf_files=[Path("manual.pdf")], documents=chunks, chunks=chunks,
                                cases=[{"id": "ING-1", "source": "manual.pdf", "fact": "2,000 operating hours"}], chunk_size=1000)

    assert check(report, "fact_coverage").status == "FAIL"


def test_fact_in_wrong_source_is_not_covered() -> None:
    chunks = [make_document(CHUNK, source="faq.pdf")]

    report = evaluate_ingestion(pdf_files=[Path("faq.pdf")], documents=chunks, chunks=chunks,
                                cases=[{"id": "ING-1", "source": "manual.pdf", "fact": "2,000 operating hours"}], chunk_size=1000)

    assert not report.cases[0]["passed"]


def test_vector_store_with_current_chunks_passes() -> None:
    chunks = [make_document(CHUNK)]

    report = evaluate_ingestion(pdf_files=[Path("manual.pdf")], documents=chunks, chunks=chunks, cases=[], chunk_size=1000, stored_texts=[CHUNK])

    assert check(report, "vector_store_up_to_date").status == "PASS"


def test_stale_vector_store_fails_even_with_same_count() -> None:
    # Same number of chunks but old content: a count comparison alone would miss this.
    chunks = [make_document(CHUNK)]

    report = evaluate_ingestion(pdf_files=[Path("manual.pdf")], documents=chunks, chunks=chunks, cases=[], chunk_size=1000,
                                stored_texts=["Old chunk produced by a previous chunker."])

    stale = check(report, "vector_store_up_to_date")

    assert stale.status == "FAIL"
    assert "ingest_documents" in stale.details[0]


def test_real_knowledge_base_ingests_cleanly(knowledge_base) -> None:
    """Offline regression test over the real PDFs: no API key or database needed."""

    report = evaluate_ingestion(pdf_files=knowledge_base["pdf_files"], documents=knowledge_base["documents"], chunks=knowledge_base["chunks"],
                                cases=load_cases("ingestion"), chunk_size=knowledge_base["chunker"].chunk_size)

    failures = {item.name: item.details for item in report.checks if item.status == "FAIL"}

    assert report.passed, failures

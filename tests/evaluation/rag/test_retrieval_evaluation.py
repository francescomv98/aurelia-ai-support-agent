import pytest
from langchain_core.documents import Document
from scripts.evaluate_rag import load_cases
from src.evaluation.rag.common import contains_phrase
from src.evaluation.rag.retrieval import evaluate_retrieval, evaluate_retrieval_case

CASE = {
    "id": "RET-1",
    "question": "What is the AIS-200 maintenance interval?",
    "relevant_sources": ["AIS-200_user_manual.pdf"],
    "facts": ["2,000 operating hours"]
}


def doc(source: str, content: str = "unrelated text") -> Document:
    return Document(page_content=content, metadata={"source": source})


def test_relevant_chunk_first_scores_perfectly() -> None:
    result = evaluate_retrieval_case(CASE, [doc("AIS-200_user_manual.pdf", "Every 2,000 operating hours."), doc("warranty_policy.pdf")])

    assert result["hit"]
    assert result["reciprocal_rank"] == 1.0
    assert result["fact_recall"] == 1.0
    assert result["context_precision"] == 0.5
    assert result["passed"]


def test_relevant_chunk_at_rank_three() -> None:
    result = evaluate_retrieval_case(CASE, [doc("a.pdf"), doc("b.pdf"), doc("AIS-200_user_manual.pdf", "Every 2,000 operating hours.")])

    assert result["reciprocal_rank"] == pytest.approx(1 / 3)


def test_no_relevant_chunk_is_a_miss() -> None:
    result = evaluate_retrieval_case(CASE, [doc("a.pdf"), doc("b.pdf")])

    assert not result["hit"]
    assert result["reciprocal_rank"] == 0.0
    assert result["missing_facts"] == ["2,000 operating hours"]
    assert not result["passed"]


def test_relevant_source_without_the_fact_fails() -> None:
    result = evaluate_retrieval_case(CASE, [doc("AIS-200_user_manual.pdf", "Installation must be done by AIS personnel.")])

    assert result["hit"]
    assert result["fact_recall"] == 0.0
    assert not result["passed"]


def test_empty_retrieval_scores_zero() -> None:
    result = evaluate_retrieval_case(CASE, [])

    assert result["context_precision"] == 0.0
    assert not result["hit"]


def test_aggregate_report_fails_below_threshold() -> None:
    def retrieve(question: str) -> list[Document]:
        return [doc("a.pdf")]

    report = evaluate_retrieval([CASE, {**CASE, "id": "RET-2"}], retrieve)

    assert not report.passed
    assert next(item for item in report.checks if item.name == "hit_rate").value == 0.0


def test_aggregate_report_passes_with_perfect_retriever() -> None:
    def retrieve(question: str) -> list[Document]:
        return [doc("AIS-200_user_manual.pdf", "Every 2,000 operating hours.")]

    report = evaluate_retrieval([CASE], retrieve)

    assert report.passed


def test_retrieval_dataset_is_answerable_from_the_knowledge_base(knowledge_base) -> None:
    """Every expected fact must exist in a listed relevant source, or the case can never pass."""

    for case in load_cases("retrieval"):
        relevant_chunks = [chunk for chunk in knowledge_base["chunks"] if chunk.metadata["source"] in case["relevant_sources"]]

        assert relevant_chunks, f"{case['id']}: no chunk from {case['relevant_sources']}"

        for fact in case["facts"]:
            assert any(contains_phrase(chunk.page_content, fact) for chunk in relevant_chunks), f"{case['id']}: '{fact}' not in relevant sources"

"""Retrieval evaluation: does the vector search return the right chunks?

Each case lists the documents that answer the question (relevant_sources) and
the facts the answer depends on. Metrics, averaged over the cases:

- hit_rate: at least one retrieved chunk comes from a relevant source
- mrr: mean reciprocal rank of the first relevant chunk
- fact_recall: share of the case's facts present in the retrieved text
- context_precision: share of retrieved chunks that come from a relevant source
"""

from collections.abc import Callable
from typing import Any
from langchain_core.documents import Document
from src.evaluation.rag.common import Check, StageReport, contains_phrase, ratio

HIT_RATE_THRESHOLD = 0.9
MRR_THRESHOLD = 0.75
FACT_RECALL_THRESHOLD = 0.85
CONTEXT_PRECISION_THRESHOLD = 0.5


def evaluate_retrieval_case(case: dict[str, Any], retrieved: list[Document]) -> dict[str, Any]:
    """Score the chunks retrieved for one question."""

    relevant_sources = set(case["relevant_sources"])
    sources = [document.metadata.get("source") for document in retrieved]
    is_relevant = [source in relevant_sources for source in sources]

    first_relevant_rank = next((rank for rank, relevant in enumerate(is_relevant, start=1) if relevant), None)

    retrieved_text = "\n".join(document.page_content for document in retrieved)
    found_facts = [fact for fact in case["facts"] if contains_phrase(retrieved_text, fact)]
    missing_facts = [fact for fact in case["facts"] if fact not in found_facts]

    return {
        "id": case["id"],
        "question": case["question"],
        "hit": first_relevant_rank is not None,
        "reciprocal_rank": 1 / first_relevant_rank if first_relevant_rank else 0.0,
        "fact_recall": ratio(len(found_facts), len(case["facts"])),
        "context_precision": ratio(sum(is_relevant), len(retrieved)) if retrieved else 0.0,
        "retrieved_sources": sources,
        "missing_facts": missing_facts,
        "passed": first_relevant_rank is not None and not missing_facts
    }


def evaluate_retrieval(cases: list[dict[str, Any]], retrieve: Callable[[str], list[Document]]) -> StageReport:
    """Run every question through the retriever and aggregate the metrics."""

    results = [evaluate_retrieval_case(case, retrieve(case["question"])) for case in cases]

    def mean(key: str) -> float:
        return sum(result[key] for result in results) / len(results) if results else 0.0

    misses = [f"{result['id']}: no relevant source in {result['retrieved_sources']}" for result in results if not result["hit"]]
    missing_facts = [f"{result['id']}: missing {result['missing_facts']}" for result in results if result["missing_facts"]]
    low_ranks = [f"{result['id']}: first relevant chunk at rank {round(1 / result['reciprocal_rank'])}"
                 for result in results if 0 < result["reciprocal_rank"] < 1]

    checks = [
        Check("hit_rate", mean("hit"), HIT_RATE_THRESHOLD, details=misses),
        Check("mrr", mean("reciprocal_rank"), MRR_THRESHOLD, details=low_ranks),
        Check("fact_recall", mean("fact_recall"), FACT_RECALL_THRESHOLD, details=missing_facts),
        # Several documents repeat the same facts, so a low precision is a signal, not a failure.
        Check("context_precision", mean("context_precision"), CONTEXT_PRECISION_THRESHOLD, level="warning")
    ]

    return StageReport(stage="retrieval", checks=checks, cases=results)

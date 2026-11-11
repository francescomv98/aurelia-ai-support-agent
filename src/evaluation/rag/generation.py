"""Generation evaluation: given the right context, does the model answer well?

Retrieval is taken out of the picture: each case gets a fixed "gold" context
selected from the ingested chunks, then goes through the production prompt.
Metrics:

- answer_correctness: answerable questions contain every required fact
- abstention: unanswerable questions are declined instead of invented
- groundedness: answers contain no number missing from the context or question
"""

import re
from collections.abc import Callable
from typing import Any
from langchain_core.documents import Document
from src.evaluation.rag.common import Check, StageReport, contains_phrase, ratio

CORRECTNESS_THRESHOLD = 0.85
ABSTENTION_THRESHOLD = 1.0
GROUNDEDNESS_THRESHOLD = 0.9
MAX_CONTEXT_CHUNKS = 4

ABSTENTION_PHRASES = (
    "not available", "not provided", "not specified", "not mentioned", "not included", "not contain", "does not include",
    "do not have", "don't have", "no information", "not able to find", "unable to find", "cannot find", "could not find",
    "isn't available", "is not covered", "not covered", "no details", "doesn't include", "doesn't contain", "doesn't provide",
    "does not provide", "not specify", "unable to provide", "cannot provide", "can't provide", "not able to provide"
)

NUMBER_PATTERN = re.compile(r"\d+(?:[.,:]\d+)*")


def select_context(case: dict[str, Any], chunks: list[Document]) -> list[Document]:
    """Pick the gold context: chunks from the case's sources that contain one of its marker phrases."""

    sources = set(case["context_sources"])

    selected = [
        chunk for chunk in chunks
        if chunk.metadata.get("source") in sources and any(contains_phrase(chunk.page_content, phrase) for phrase in case["context_contains"])
    ]

    return selected[:MAX_CONTEXT_CHUNKS]


def extract_numbers(text: str) -> set[str]:
    """Return the multi-digit numbers in a text, with thousands separators removed.

    Single digits are ignored: they are mostly list numbering ("1. Stop the machine").
    """

    numbers = set()

    for match in NUMBER_PATTERN.findall(text):
        normalized = re.sub(r"(?<=\d),(?=\d{3}\b)", "", match)

        if sum(character.isdigit() for character in normalized) >= 2:
            numbers.add(normalized)

    return numbers


def unsupported_numbers(answer: str, context: str, question: str, allowed: list[str] | None = None) -> list[str]:
    """Numbers in the answer that appear in neither the context, the question nor the allowed list."""

    supported = extract_numbers(context) | extract_numbers(question) | extract_numbers(" ".join(allowed or []))

    return sorted(extract_numbers(answer) - supported)


def evaluate_generation_case(case: dict[str, Any], answer: str, context: str) -> dict[str, Any]:
    """Score one generated answer against its gold context."""

    answerable = case.get("answerable", True)

    if answerable:
        # Each entry is a required fact; a list gives accepted alternative wordings.
        required = [entry if isinstance(entry, list) else [entry] for entry in case["must_include"]]
        missing = [alternatives[0] for alternatives in required if not any(contains_phrase(answer, phrase) for phrase in alternatives)]
        correct = not missing
    else:
        missing = []
        correct = any(contains_phrase(answer, phrase) for phrase in ABSTENTION_PHRASES)

    unsupported = unsupported_numbers(answer, context, case["question"], case.get("allowed_numbers"))

    return {
        "id": case["id"],
        "question": case["question"],
        "answerable": answerable,
        "correct": correct,
        "missing_facts": missing,
        "grounded": not unsupported,
        "unsupported_numbers": unsupported,
        "answer": answer,
        "passed": correct and not unsupported
    }


def evaluate_generation(cases: list[dict[str, Any]], chunks: list[Document], generate: Callable[[str, list[Document]], str]) -> StageReport:
    """Generate an answer for every case from its gold context and aggregate the metrics."""

    results = []
    empty_contexts = []

    for case in cases:
        context_documents = select_context(case, chunks)

        if not context_documents:
            empty_contexts.append(case["id"])

        answer = generate(case["question"], context_documents)
        context_text = "\n".join(document.page_content for document in context_documents)

        result = evaluate_generation_case(case, answer, context_text)
        result["context_sources"] = [document.metadata.get("source") for document in context_documents]
        results.append(result)

    answerable = [result for result in results if result["answerable"]]
    unanswerable = [result for result in results if not result["answerable"]]

    checks = [
        Check("gold_context_found", ratio(len(cases) - len(empty_contexts), len(cases)), 1.0, details=empty_contexts),
        Check("answer_correctness", ratio(sum(result["correct"] for result in answerable), len(answerable)), CORRECTNESS_THRESHOLD,
              details=[f"{result['id']}: missing {result['missing_facts']}" for result in answerable if not result["correct"]]),
        Check("abstention", ratio(sum(result["correct"] for result in unanswerable), len(unanswerable)), ABSTENTION_THRESHOLD,
              details=[f"{result['id']}: answered instead of declining" for result in unanswerable if not result["correct"]]),
        Check("groundedness", ratio(sum(result["grounded"] for result in results), len(results)), GROUNDEDNESS_THRESHOLD,
              details=[f"{result['id']}: unsupported numbers {result['unsupported_numbers']}" for result in results if not result["grounded"]])
    ]

    return StageReport(stage="generation", checks=checks, cases=results)

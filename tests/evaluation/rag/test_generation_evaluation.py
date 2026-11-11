from langchain_core.documents import Document
from scripts.evaluate_rag import load_cases
from src.evaluation.rag.common import contains_phrase
from src.evaluation.rag.generation import (evaluate_generation, evaluate_generation_case, extract_numbers, select_context,
                                           unsupported_numbers)

CONTEXT = "AIS-200: preventive maintenance every 2,000 operating hours. Standard warranty: 24 months from installation."

ANSWERABLE = {
    "id": "GEN-1",
    "question": "What is the AIS-200 maintenance interval?",
    "context_sources": ["preventive_maintenance.pdf"],
    "context_contains": ["2,000 operating hours"],
    "must_include": ["2,000 operating hours"]
}

UNANSWERABLE = {
    "id": "GEN-2",
    "question": "What is the price of an AIS-200?",
    "context_sources": ["preventive_maintenance.pdf"],
    "context_contains": ["2,000 operating hours"],
    "answerable": False
}


def test_extract_numbers_ignores_separators_and_list_numbering() -> None:
    assert extract_numbers("1. Stop. Every 2,000 hours, 08:00, 1.5 bar") == {"2000", "08:00", "1.5"}


def test_unsupported_numbers_flags_invented_values() -> None:
    assert unsupported_numbers("Every 2000 hours, costs 45,000 EUR.", CONTEXT, "question") == ["45000"]


def test_unsupported_numbers_accepts_question_and_allowed_numbers() -> None:
    answer = "With 2,300 hours, 200 hours remain."

    assert unsupported_numbers(answer, CONTEXT, "My machine has 2,300 hours.", allowed=["200"]) == []


def test_correct_grounded_answer_passes() -> None:
    result = evaluate_generation_case(ANSWERABLE, "Maintenance is due every 2,000 operating hours.", CONTEXT)

    assert result["correct"]
    assert result["grounded"]
    assert result["passed"]


def test_answer_with_wrong_number_fails() -> None:
    result = evaluate_generation_case(ANSWERABLE, "Maintenance is due every 2,500 operating hours.", CONTEXT)

    assert not result["correct"]
    assert result["unsupported_numbers"] == ["2500"]


def test_alternative_wordings_are_accepted() -> None:
    case = {**ANSWERABLE, "must_include": [["disable the alarm", "disabling the alarm"]]}

    assert evaluate_generation_case(case, "Avoid disabling the alarm.", CONTEXT)["correct"]


def test_unanswerable_question_must_be_declined() -> None:
    declined = evaluate_generation_case(UNANSWERABLE, "The price is not provided in the documentation.", CONTEXT)
    invented = evaluate_generation_case(UNANSWERABLE, "The AIS-200 costs 45,000 EUR.", CONTEXT)

    assert declined["passed"]
    assert not invented["correct"]
    assert not invented["grounded"]


def test_real_model_refusal_wording_counts_as_declining() -> None:
    # Wording returned by gpt-4o-mini in a live run; it was wrongly scored as an answer at first.
    answer = ("The provided context does not specify the number of employees at Aurelia Industrial Systems. "
              "Therefore, I am unable to provide that information.")

    assert evaluate_generation_case(UNANSWERABLE, answer, CONTEXT)["correct"]


def test_select_context_filters_by_source_and_marker() -> None:
    chunks = [
        Document(page_content=CONTEXT, metadata={"source": "preventive_maintenance.pdf"}),
        Document(page_content=CONTEXT, metadata={"source": "customer_faq.pdf"}),
        Document(page_content="Unrelated text.", metadata={"source": "preventive_maintenance.pdf"})
    ]

    assert select_context(ANSWERABLE, chunks) == [chunks[0]]


def test_evaluate_generation_passes_gold_context_to_the_model() -> None:
    chunks = [Document(page_content=CONTEXT, metadata={"source": "preventive_maintenance.pdf"})]
    calls = []

    def generate(question: str, context: list[Document]) -> str:
        calls.append((question, context))
        return "Every 2,000 operating hours." if "interval" in question else "That information is not available."

    report = evaluate_generation([ANSWERABLE, UNANSWERABLE], chunks, generate)

    assert report.passed
    assert calls[0] == (ANSWERABLE["question"], chunks)


def test_generation_dataset_gold_context_holds_the_answers(knowledge_base) -> None:
    """Each gold context must exist and contain the required facts, or the model is tested on missing data."""

    for case in load_cases("generation"):
        context = select_context(case, knowledge_base["chunks"])

        assert context, f"{case['id']}: no gold context found"

        if not case.get("answerable", True):
            continue

        context_text = "\n".join(chunk.page_content for chunk in context)
        computed = set(case.get("allowed_numbers", []))

        for entry in case["must_include"]:
            alternatives = entry if isinstance(entry, list) else [entry]

            if set(alternatives) <= computed:
                continue  # a calculated value, such as remaining hours, is not in the text

            assert any(contains_phrase(context_text, phrase) for phrase in alternatives), f"{case['id']}: {alternatives} not in gold context"

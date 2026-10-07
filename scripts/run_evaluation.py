import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "data" / "evaluation" / "evaluation_dataset.json"

VALID_CATEGORIES = {"rag", "tool", "authorization", "hitl", "hybrid", "edge"}


def load_dataset() -> list[dict]:
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_case(case: dict) -> tuple[bool, str]:
    required_fields = {"id", "category", "question", "expected"}

    missing_fields = required_fields - case.keys()

    if missing_fields:
        return False, f"Missing fields: {sorted(missing_fields)}"

    if case["category"] not in VALID_CATEGORIES:
        return False, f"Invalid category: {case['category']}"

    if not isinstance(case["question"], str) or not case["question"].strip():
        return False, "Question cannot be empty."

    if not isinstance(case["expected"], str) or not case["expected"].strip():
        return False, "Expected value cannot be empty."

    return True, ""


def run_deterministic_evaluation() -> int:
    dataset = load_dataset()

    passed = 0
    failed = 0

    print("Aurelia AI Support Agent Evaluation")
    print("=" * 40)
    print()
    print(f"Dataset cases: {len(dataset)}")
    print()

    for case in dataset:
        is_valid, error = validate_case(case)

        if is_valid:
            passed += 1
            print(f"[PASS] {case['id']}")
        else:
            failed += 1
            print(f"[FAIL] {case.get('id', 'UNKNOWN')}: {error}")

    print()
    print("=" * 40)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Score: {passed / len(dataset) * 100:.1f}%")
    print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run_deterministic_evaluation())
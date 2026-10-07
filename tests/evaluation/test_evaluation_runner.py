from scripts.run_evaluation import load_dataset, validate_case

def test_evaluation_dataset_can_be_loaded() -> None:
    dataset = load_dataset()

    assert isinstance(dataset, list)
    assert len(dataset) > 0


def test_evaluation_dataset_contains_required_fields() -> None:
    dataset = load_dataset()

    required_fields = {"id", "category", "question", "expected"}

    for case in dataset:
        assert required_fields.issubset(case.keys())


def test_evaluation_dataset_contains_unique_ids() -> None:
    dataset = load_dataset()

    ids = [case["id"] for case in dataset]

    assert len(ids) == len(set(ids))


def test_evaluation_cases_are_valid() -> None:
    dataset = load_dataset()

    for case in dataset:
        is_valid, error = validate_case(case)

        assert is_valid, error
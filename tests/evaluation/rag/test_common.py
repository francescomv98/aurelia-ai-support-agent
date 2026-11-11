from src.evaluation.rag.common import Check, StageReport, contains_phrase


def test_contains_phrase_matches_whole_words_only() -> None:
    # "80 units per minute" must not match the AIS-500's "180 units per minute".
    assert contains_phrase("Capacity: 80 units per minute.", "80 units per minute")
    assert not contains_phrase("Capacity: 180 units per minute.", "80 units per minute")


def test_contains_phrase_normalizes_numbers_dashes_and_case() -> None:
    assert contains_phrase("Every 2,000 Operating Hours.", "2000 operating hours")
    assert contains_phrase("Monday–Friday, 08:00–18:00 CET/CEST", "08:00-18:00 cet/cest")


def test_contains_phrase_rejects_empty_phrase() -> None:
    assert not contains_phrase("any text", "   ")


def test_warning_check_does_not_fail_stage() -> None:
    report = StageReport(stage="ingestion", checks=[
        Check("hard", 1.0, 1.0),
        Check("soft", 0.5, 1.0, level="warning")
    ])

    assert report.passed
    assert report.checks[1].status == "WARN"


def test_error_check_fails_stage() -> None:
    report = StageReport(stage="retrieval", checks=[Check("hit_rate", 0.8, 0.9)])

    assert not report.passed
    assert report.to_dict()["checks"][0]["status"] == "FAIL"

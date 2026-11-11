import re
from dataclasses import dataclass, field
from typing import Any, Literal
from src.evaluation.evaluator import normalize_text


def contains_phrase(text: str, phrase: str) -> bool:
    """Return True when the normalized phrase appears in the text as whole words.

    A plain substring test is not enough: "80 units per minute" would match
    inside "180 units per minute".
    """

    normalized_phrase = normalize_text(phrase)

    if not normalized_phrase:
        return False

    pattern = rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)"

    return re.search(pattern, normalize_text(text)) is not None


@dataclass
class Check:
    """One aggregate metric compared against its threshold.

    A check with level "warning" is reported but does not fail the stage.
    """

    name: str
    value: float
    threshold: float
    level: Literal["error", "warning"] = "error"
    details: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.value >= self.threshold

    @property
    def status(self) -> str:
        if self.passed:
            return "PASS"

        return "FAIL" if self.level == "error" else "WARN"


@dataclass
class StageReport:
    """Result of evaluating one RAG stage."""

    stage: str
    checks: list[Check]
    cases: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks if check.level == "error")

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "passed": self.passed,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "value": round(check.value, 4),
                    "threshold": check.threshold,
                    "level": check.level,
                    "details": check.details
                }
                for check in self.checks
            ],
            "cases": self.cases
        }


def ratio(numerator: int, denominator: int) -> float:
    """Return numerator / denominator, or 1.0 when there is nothing to measure."""

    return numerator / denominator if denominator else 1.0

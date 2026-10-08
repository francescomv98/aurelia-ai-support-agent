import re
from typing import Any
from src.services.exceptions import AuthorizationError

def normalize_text(text: str) -> str:
    """Normalize text for evaluation comparisons."""

    normalized = text.lower()
    normalized = re.sub(r"(?<=\d),(?=\d)", "", normalized)
    normalized = re.sub(r"\bfrom\s+(?=\d{2}:\d{2})", "", normalized)
    normalized = re.sub(r"\boperating\s+hours\b", "hours", normalized)
    normalized = re.sub(r"[-–—]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def evaluate_rag(expected: str, actual: str) -> tuple[bool, str]:
    expected_normalized = normalize_text(expected)
    actual_normalized = normalize_text(actual)

    if expected_normalized in actual_normalized:
        return True, "Expected RAG information found in agent response."

    if expected_normalized.startswith("stop the machine safely"):
        expected_phrases = ["stop the machine safely", "cooling system", "coolant", "leak", "cooling unit"]
        
        safety_requirement_found = ("must not bypass" in actual_normalized or "must not: bypass" in actual_normalized or 
                                    "must not bypass temperature protection" in actual_normalized or "bypass temperature protection" in actual_normalized)
        
        missing_phrases = [phrase for phrase in expected_phrases if phrase not in actual_normalized]

        if not safety_requirement_found:
            missing_phrases.append("safety threshold must not be bypassed")

        if not missing_phrases:
            return True, "Expected RAG information found in agent response."

        return False, f"Missing expected RAG information: {missing_phrases}"

    return False, "Expected RAG information was not found."


def evaluate_tool(expected: str, actual: str) -> tuple[bool, str]:
    """Evaluate an enterprise tool response by checking expected information."""

    expected_values = [normalize_text(value) for value in expected.split(",") if value.strip()]

    actual_normalized = normalize_text(actual)

    missing_values = [value for value in expected_values if value not in actual_normalized]

    if not missing_values:
        return True, "All expected tool information was found."

    return False, f"Missing expected tool information: {missing_values}"


def evaluate_authorization(expected: str, result: dict[str, Any]) -> tuple[bool, str]:
    """Evaluate whether an authorization scenario behaved as expected."""

    expected = expected.upper()

    if expected == "AUTHORIZED":
        if "response" in result or "tool_result" in result:
            return True, "Authorized request completed successfully."

        return False, "Authorized request did not produce a result."

    if expected == "REJECTED":
        error = result.get("error")

        if isinstance(error, AuthorizationError):
            return True, "Unauthorized request was rejected by authorization controls."

        actual_response = normalize_text(str(result.get("response", "")))
        actual_tool_result = normalize_text(str(result.get("tool_result", "")))
        actual = f"{actual_response} {actual_tool_result}".strip()

        if "order not found" in actual:
            return True, "Unauthorized request was rejected without revealing protected resource information."

        return False, "Unauthorized request was not rejected by authorization controls."

    return False, f"Unsupported authorization expectation: {expected}"


def evaluate_hitl(result: dict[str, Any]) -> tuple[bool, str]:
    """Evaluate whether human approval was requested."""

    interrupt_data = result.get("__interrupt__")

    if interrupt_data:
        return True, "Human approval was requested."

    return False, "Human approval was not requested."


def evaluate_hybrid(expected: str, actual: str) -> tuple[bool, str]:
    """Evaluate a hybrid response by checking all expected values."""

    expected_values = [normalize_text(value) for value in expected.split(",") if value.strip()]

    actual_normalized = normalize_text(actual)

    missing_values = [value for value in expected_values if value not in actual_normalized]

    if not missing_values:
        return True, "All expected hybrid information was found."

    return False, f"Missing expected hybrid information: {missing_values}"


def evaluate_edge(expected: str, actual: str) -> tuple[bool, str]:
    """Evaluate an edge-case response."""

    expected_lower = normalize_text(expected)
    actual_lower = normalize_text(actual)

    if expected_lower == "order not found":
        if "order not found" in actual_lower:
            return True, "Expected edge-case behavior was found."

        return False, "Expected order-not-found behavior was not found."

    if expected_lower == "clarification":
        clarification_keywords = ("how can i help", "how can i assist", "what can i help", "more information", "clarify", "what do you need", "how may i help")

        if any(keyword in actual_lower for keyword in clarification_keywords):
            return True, "Agent requested clarification."

        return False, "Agent did not request clarification."

    return False, f"Unsupported edge-case expectation: {expected}"


def evaluate_case(case: dict[str, Any], result: dict[str, Any]) -> tuple[bool, str]:
    """Evaluate a single evaluation case."""

    category = case["category"]

    if category == "hitl":
        return evaluate_hitl(result)

    error = result.get("error")

    if category == "authorization":
        return evaluate_authorization(case["expected"], result)

    if error is not None:
        return False, f"Agent execution failed: {error}"

    actual_response = str(result.get("response", "")).strip()
    tool_result = str(result.get("tool_result", "")).strip()
    actual = f"{actual_response} {tool_result}".strip()

    print(f"\n[DEBUG] Agent response:\n{actual_response}")
    print(f"[DEBUG] Tool result:\n{tool_result}")

    if not actual:
        return False, "Agent returned an empty result."

    if category == "rag":
        return evaluate_rag(case["expected"], actual)

    if category == "tool":
        return evaluate_tool(case["expected"], actual)

    if category == "hybrid":
        return evaluate_hybrid(case["expected"], actual)

    if category == "edge":
        return evaluate_edge(case["expected"], actual)

    return False, f"Unsupported evaluation category: {category}"

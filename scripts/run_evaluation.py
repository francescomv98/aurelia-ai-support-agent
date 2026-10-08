import json
from pathlib import Path
from typing import Any
from langgraph.types import Command
from src.agent.checkpointer import create_async_checkpointer
from src.agent.graph import build_agent_graph
from src.agent.state import AgentState
from src.auth.models import AuthenticatedUser, UserRole
from src.database.session import SessionLocal
from src.llm.openai_client import create_chat_model
from src.rag.rag_service import RAGService
from src.rag.embedding import create_embeddings
from src.rag.vector_store import VectorStore
from src.rag.retriever import Retriever
from src.evaluation.evaluator import evaluate_case
from src.logging.logger import logger
import asyncio
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "data" / "evaluation" / "evaluation_dataset.json"

VALID_CATEGORIES = {"rag", "tool", "authorization", "hitl", "hybrid", "edge", "security"}

EVALUATION_USERS = {
    1: 1,  # Alfa Manufacturing -> alfa.support
    2: 2,  # Beta Automation -> beta.operations
    3: 3,  # Gamma Industries -> gamma.manager
    4: 4,  # Delta Mechanics -> delta.maintenance
    5: 5   # Nova Production -> nova.operator
}


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


def create_evaluation_state(case: dict, user: AuthenticatedUser) -> AgentState:
    return {
        "user_query": case["question"],
        "authenticated_user": user,
        "route": "rag",
        "retrieved_context": [],
        "rag_available": True,
        "tool_type": None,
        "pending_action": None,
        "tool_result": "",
        "response": ""
    }


def create_evaluation_user(case: dict) -> AuthenticatedUser:
    customer_id = case.get("authenticated_customer_id", 1)

    user_id = EVALUATION_USERS.get(customer_id)

    if user_id is None:
        raise ValueError(f"No evaluation user configured for customer {customer_id}.")

    return AuthenticatedUser(user_id=user_id, customer_id=customer_id, role=UserRole.CUSTOMER)


async def execute_evaluation_case(agent_graph: Any, case: dict, user: AuthenticatedUser) -> dict:
    state = create_evaluation_state(case, user)
    config = {"configurable": {"thread_id": f"evaluation-{case['id']}"}}

    try:
        result = await agent_graph.ainvoke(state, config=config)

        if case["category"] == "authorization" and result.get("__interrupt__"):
            logger.info("Resuming authorization evaluation after human approval", case_id=case["id"])

            result = await agent_graph.ainvoke(Command(resume="APPROVED"), config=config)

        return result

    except Exception as exc:
        logger.exception("Evaluation case execution failed", case_id=case["id"])
        return {
            "error": exc
        }


def evaluate_evaluation_case(case: dict, result: dict) -> dict:
    passed, reason = evaluate_case(case=case, result=result)

    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "expected": case["expected"],
        "passed": passed,
        "reason": reason,
        "response": result.get("response", ""),
        "tool_result": result.get("tool_result", "")
    }


def create_evaluation_rag_service() -> RAGService:
    embeddings = create_embeddings()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    vector_store = VectorStore(connection=database_url, embeddings=embeddings)

    retriever = Retriever(vector_store=vector_store)

    return RAGService(retriever=retriever)


async def run_live_evaluation_case(case: dict, user: AuthenticatedUser) -> dict:
    db = SessionLocal()
    checkpointer = None
    connection = None

    try:
        checkpointer, connection = await create_async_checkpointer()

        chat_model = create_chat_model()
        rag_service = create_evaluation_rag_service()

        agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

        return await execute_evaluation_case(agent_graph=agent_graph, case=case, user=user)

    finally:
        if connection is not None:
            await connection.close()

        db.close()


async def run_live_evaluation() -> int:
    dataset = load_dataset()

    print("Aurelia AI Support Agent - Live Evaluation")
    print("=" * 50)
    print()
    print(f"Dataset cases: {len(dataset)}")
    print()

    results = []

    for case in dataset:
        print(f"Running {case['id']}...")

        is_valid, error = validate_case(case)

        if not is_valid:
            result = {
                "id": case.get("id", "UNKNOWN"),
                "category": case.get("category", "UNKNOWN"),
                "question": case.get("question", ""),
                "expected": case.get("expected", ""),
                "passed": False,
                "reason": error,
                "response": "",
                "tool_result": ""
            }

            results.append(result)
            print(f"[FAIL] {case.get('id', 'UNKNOWN')}: {error}")
            continue

        user = create_evaluation_user(case)

        execution_result = await run_live_evaluation_case(case=case, user=user)

        evaluation_result = evaluate_evaluation_case(case=case, result=execution_result)

        results.append(evaluation_result)

        status = "PASS" if evaluation_result["passed"] else "FAIL"

        print(f"[{status}] {case['id']}: {evaluation_result['reason']}")

    passed = sum(1 for result in results if result["passed"])
    failed = len(results) - passed

    print()
    print("=" * 50)
    print("Live Evaluation Summary")
    print("=" * 50)
    print(f"Total:  {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Score:  {passed / len(results) * 100:.1f}%")
    print()

    if failed:
        print("Failed cases:")
        for result in results:
            if not result["passed"]:
                print(f"- {result['id']}: {result['reason']}")
        print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if os.name == "nt":
        raise SystemExit(asyncio.run(run_live_evaluation(), loop_factory=asyncio.SelectorEventLoop))
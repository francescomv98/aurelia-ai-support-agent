"""Evaluate the RAG pipeline stage by stage: ingestion, retrieval and generation.

Usage, from the repository root:

    python -m scripts.evaluate_rag                       # all three stages
    python -m scripts.evaluate_rag --stage ingestion     # offline, no API key needed
    python -m scripts.evaluate_rag --stage ingestion --check-store
    python -m scripts.evaluate_rag --stage retrieval --top-k 4
    python -m scripts.evaluate_rag --stage generation
    python -m scripts.evaluate_rag --output data/evaluation/rag/rag_report.json

Requirements per stage:
- ingestion: only the PDFs (--check-store also needs DATABASE_URL)
- retrieval: DATABASE_URL, OPENAI_API_KEY and documents already ingested
- generation: OPENAI_API_KEY
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from langchain_core.documents import Document
from sqlalchemy import create_engine, text
from src.app_logging.logger import configure_logging
from src.evaluation.rag.common import StageReport
from src.evaluation.rag.generation import evaluate_generation
from src.evaluation.rag.ingestion import evaluate_ingestion, vector_store_check
from src.evaluation.rag.retrieval import evaluate_retrieval
from src.rag.chunker import DocumentChunker
from src.rag.document_loader import DocumentLoader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_PATH = PROJECT_ROOT / "data" / "documents"
DATASET_DIRECTORY = PROJECT_ROOT / "data" / "evaluation" / "rag"
COLLECTION_NAME = "aurelia_documents"
STAGES = ("ingestion", "retrieval", "generation")


def load_cases(stage: str) -> list[dict[str, Any]]:
    with (DATASET_DIRECTORY / f"{stage}_cases.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_knowledge_base(chunker: DocumentChunker) -> tuple[list[Path], list[Document], list[Document]]:
    """Load and chunk the PDFs exactly as scripts/ingest_documents.py does."""

    pdf_files = sorted(DOCUMENTS_PATH.rglob("*.pdf"))
    documents = DocumentLoader().load_directory(DOCUMENTS_PATH)
    chunks = chunker.split(documents)

    return pdf_files, documents, chunks


def load_stored_chunk_texts(database_url: str) -> list[str]:
    """Return the text of every chunk stored in the PGVector collection."""

    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            return list(connection.execute(
                text(
                    "SELECT e.document FROM langchain_pg_embedding e "
                    "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
                    "WHERE c.name = :name"
                ),
                {"name": COLLECTION_NAME}
            ).scalars())
    finally:
        engine.dispose()


def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"{name} environment variable is not set.")

    return value


def run_ingestion(check_store: bool) -> StageReport:
    chunker = DocumentChunker()
    pdf_files, documents, chunks = load_knowledge_base(chunker)

    stored_texts = load_stored_chunk_texts(require_env("DATABASE_URL")) if check_store else None

    return evaluate_ingestion(pdf_files=pdf_files, documents=documents, chunks=chunks, cases=load_cases("ingestion"),
                              chunk_size=chunker.chunk_size, stored_texts=stored_texts)


def run_retrieval(top_k: int) -> StageReport:
    from src.rag.embedding import create_embeddings
    from src.rag.retriever import Retriever
    from src.rag.vector_store import VectorStore

    database_url = require_env("DATABASE_URL")
    vector_store = VectorStore(connection=database_url, embeddings=create_embeddings(), collection_name=COLLECTION_NAME)
    retriever = Retriever(vector_store=vector_store, top_k=top_k)

    report = evaluate_retrieval(cases=load_cases("retrieval"), retrieve=retriever.retrieve)

    # Metrics from an out-of-date index describe the old chunker, not the current code.
    _, _, chunks = load_knowledge_base(DocumentChunker())
    report.checks.insert(0, vector_store_check(load_stored_chunk_texts(database_url), chunks))

    return report


def run_generation() -> StageReport:
    from src.agent.graph import generate_response
    from src.llm.openai_client import create_chat_model
    from src.rag.rag_service import RAGService

    chat_model = create_chat_model()
    rag_service = RAGService(retriever=None)  # only build_context is used

    def generate(question: str, context: list[Document]) -> str:
        # Same node and prompt the agent uses for documentation questions.
        state = {
            "user_query": question,
            "route": "rag",
            "rag_available": True,
            "retrieved_context": context,
            "tool_result": "",
            "response": ""
        }

        return str(generate_response(state, chat_model, rag_service)["response"])

    _, _, chunks = load_knowledge_base(DocumentChunker())

    return evaluate_generation(cases=load_cases("generation"), chunks=chunks, generate=generate)


def print_report(number: int, report: StageReport) -> None:
    title = f"{number}. {report.stage.upper()}"

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)

    for check in report.checks:
        print(f"[{check.status}] {check.name:<28} {check.value:6.3f}  (threshold {check.threshold:.2f})")

        for detail in check.details[:10]:
            print(f"         - {detail}")

        if len(check.details) > 10:
            print(f"         ... and {len(check.details) - 10} more")

    failed_cases = [case for case in report.cases if not case.get("passed", True)]

    print()
    print(f"Cases: {len(report.cases) - len(failed_cases)}/{len(report.cases)} passed")

    for case in failed_cases:
        print(f"  [FAIL] {case['id']}")

        if case.get("answer"):
            print(f"         answer: {case['answer'][:300]}")

    print(f"Stage result: {'PASS' if report.passed else 'FAIL'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the RAG pipeline stage by stage.")
    parser.add_argument("--stage", choices=(*STAGES, "all"), default="all")
    parser.add_argument("--top-k", type=int, default=4, help="Chunks retrieved per question (the agent uses 4).")
    parser.add_argument("--check-store", action="store_true", help="Also compare the chunk count with the vector store.")
    parser.add_argument("--output", type=Path, help="Write the full report, including every answer, to a JSON file.")
    args = parser.parse_args()

    # Facts such as "5–35 °C" would crash a cp1252 Windows console.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    load_dotenv()
    configure_logging()
    logging.getLogger().setLevel(logging.WARNING)

    stages = STAGES if args.stage == "all" else (args.stage,)
    runners = {
        "ingestion": lambda: run_ingestion(args.check_store),
        "retrieval": lambda: run_retrieval(args.top_k),
        "generation": run_generation
    }

    print("Aurelia AI Support Agent - RAG Evaluation")

    reports: list[StageReport] = []
    errors: dict[str, str] = {}

    for stage in stages:
        try:
            report = runners[stage]()
        except Exception as exc:
            # One stage failing to start (missing key, database down) must not hide the others.
            errors[stage] = f"{type(exc).__name__}: {exc}"
            print()
            print(f"{STAGES.index(stage) + 1}. {stage.upper()}: could not run - {errors[stage]}")
            continue

        reports.append(report)
        print_report(STAGES.index(stage) + 1, report)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for report in reports:
        print(f"{report.stage:<12} {'PASS' if report.passed else 'FAIL'}")

    for stage, error in errors.items():
        print(f"{stage:<12} ERROR ({error})")

    if args.output:
        args.output.write_text(
            json.dumps({"reports": [report.to_dict() for report in reports], "errors": errors}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\nFull report written to {args.output}")

    return 0 if reports and not errors and all(report.passed for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())

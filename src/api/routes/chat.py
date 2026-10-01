import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.agent.graph import build_agent_graph
from src.api.dependencies import get_current_user
from src.auth.models import AuthenticatedUser
from src.database.session import SessionLocal
from src.llm.openai_client import create_chat_model
from src.logging.logger import logger
from src.rag.embedding import create_embeddings
from src.rag.rag_service import RAGService
from src.rag.retriever import Retriever
from src.rag.vector_store import VectorStore

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    """Request payload for the support agent."""

    message: str


class ChatResponse(BaseModel):
    """Response returned by the support agent."""

    response: str


def create_rag_service() -> RAGService:
    """Create the RAG service and its dependencies."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    embeddings = create_embeddings()

    vector_store = VectorStore(connection=database_url, embeddings=embeddings)

    retriever = Retriever(vector_store=vector_store, top_k=4)

    return RAGService(retriever=retriever)


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, current_user: AuthenticatedUser = Depends(get_current_user)) -> ChatResponse:
    """Process a user message through the support agent."""

    logger.info("Chat request received", user_id=current_user.user_id, role=current_user.role.value, message_length=len(request.message))

    if not request.message.strip():
        return ChatResponse(response="Please provide a message.")

    db = SessionLocal()

    try:
        chat_model = create_chat_model()
        rag_service = create_rag_service()

        agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db)

        initial_state = {
            "user_query": request.message,
            "authenticated_user": current_user,
            "route": "rag",
            "retrieved_context": [],
            "tool_type": None,
            "tool_result": "",
            "response": ""
        }

        result = agent_graph.invoke(initial_state)

        logger.info("Chat request completed", user_id=current_user.user_id)

        return ChatResponse(response=result["response"])

    except Exception:
        logger.exception("Chat request failed", user_id=current_user.user_id)
        raise

    finally:
        db.close()
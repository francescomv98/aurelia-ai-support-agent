import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from functools import lru_cache
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
from src.agent.checkpointer import create_checkpointer
import uuid

router = APIRouter(prefix="/chat", tags=["chat"])

@lru_cache(maxsize=1)
def get_checkpointer():
    """Create and cache the PostgreSQL LangGraph checkpointer."""
    return create_checkpointer()

class ChatRequest(BaseModel):
    """Request payload for the support agent."""

    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    """Response returned by the support agent."""

    response: str
    thread_id: str


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
async def chat(request: ChatRequest, current_user: AuthenticatedUser = Depends(get_current_user)) -> ChatResponse:
    """Process a user message through the support agent."""

    logger.info("Chat request received", user_id=current_user.user_id, role=current_user.role.value, message_length=len(request.message))

    if not request.message.strip():
        return ChatResponse(response="Please provide a message.", thread_id=request.thread_id or str(uuid.uuid4()))
    
    thread_id = request.thread_id or str(uuid.uuid4())

    db = SessionLocal()

    try:
        chat_model = create_chat_model()
        rag_service = create_rag_service()
        checkpointer = get_checkpointer()

        agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

        initial_state = {
            "user_query": request.message,
            "authenticated_user": current_user,
            "route": "rag",
            "retrieved_context": [],
            "rag_available": True,
            "tool_type": None,
            "pending_action": None,
            "tool_result": "",
            "response": ""
        }

        config = { "configurable": { "thread_id": thread_id } }

        result = await agent_graph.ainvoke(initial_state, config=config)

        logger.info("Chat request completed", user_id=current_user.user_id)

        return ChatResponse(response=result["response"], thread_id=thread_id)

    except Exception:
        logger.exception("Chat request failed", user_id=current_user.user_id, thread_id=thread_id)
        raise

    finally:
        db.close()
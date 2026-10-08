import os
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from src.agent.graph import build_agent_graph
from src.agent.checkpointer import create_async_checkpointer
from src.api.dependencies import get_current_user
from src.auth.models import AuthenticatedUser
from src.database.session import SessionLocal
from src.llm.openai_client import create_chat_model
from src.logging.logger import logger
from src.rag.embedding import create_embeddings
from src.rag.rag_service import RAGService
from src.rag.retriever import Retriever
from src.rag.vector_store import VectorStore
from langgraph.types import Command
from typing import Literal
import uuid

router = APIRouter(prefix="/chat", tags=["chat"])

_checkpointer = None
_checkpointer_pool = None


async def get_checkpointer():
    """Create and cache the asynchronous PostgreSQL LangGraph checkpointer."""
    global _checkpointer, _checkpointer_pool

    if _checkpointer is None:
        _checkpointer, _checkpointer_pool = await create_async_checkpointer()

    return _checkpointer


class ChatRequest(BaseModel):
    """Request payload for the support agent."""

    message: str
    thread_id: str | None = None


class ChatResumeRequest(BaseModel):
    """Request payload used to resume a paused agent workflow."""

    thread_id: str
    decision: Literal["APPROVED", "REJECTED"]


class ApprovalResponse(BaseModel):
    """Human approval request returned when the agent pauses."""

    action_type: str
    description: str
    parameters: dict


class ChatResponse(BaseModel):
    """Response returned by the support agent."""

    status: str = "completed"
    response: str | None = None
    thread_id: str
    approval: ApprovalResponse | None = None


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
        checkpointer = await get_checkpointer()

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

        interrupts = result.get("__interrupt__")

        if interrupts:
            interrupt_value = interrupts[0].value

            logger.info("Human approval required", user_id=current_user.user_id, thread_id=thread_id, action_type=interrupt_value.get("action_type"))

            return ChatResponse(
                status="approval_required",
                thread_id=thread_id,
                approval=ApprovalResponse(
                    action_type=interrupt_value["action_type"],
                    description=interrupt_value["description"],
                    parameters=interrupt_value["parameters"]
                )
            )

        logger.info("Chat request completed", user_id=current_user.user_id, thread_id=thread_id)

        return ChatResponse(
            status="completed",
            response=result["response"],
            thread_id=thread_id
        )

    except Exception:
        logger.exception("Chat request failed", user_id=current_user.user_id, thread_id=thread_id)
        raise

    finally:
        db.close()


@router.post("/resume", response_model=ChatResponse)
async def resume_chat(request: ChatResumeRequest, current_user: AuthenticatedUser = Depends(get_current_user)) -> ChatResponse:
    """Resume a paused support agent workflow after human approval."""

    logger.info("Chat resume request received", user_id=current_user.user_id, thread_id=request.thread_id, decision=request.decision)

    db = SessionLocal()

    try:
        chat_model = create_chat_model()
        rag_service = create_rag_service()
        checkpointer = await get_checkpointer()

        agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

        config = {"configurable": {"thread_id": request.thread_id}}

        state_snapshot = await agent_graph.aget_state(config)

        if not state_snapshot.values:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat thread not found."
            )

        thread_user = state_snapshot.values.get("authenticated_user")

        if thread_user is None:
            logger.warning("Chat thread has no authenticated user", thread_id=request.thread_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chat thread ownership could not be verified."
            )

        if thread_user.user_id != current_user.user_id:
            logger.warning("Unauthorized chat thread access attempt", user_id=current_user.user_id, thread_id=request.thread_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to resume this chat thread."
            )

        if not state_snapshot.next:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat thread is not waiting for human approval."
            )
        
        result = await agent_graph.ainvoke(Command(resume=request.decision), config=config)

        interrupts = result.get("__interrupt__")

        if interrupts:
            interrupt_value = interrupts[0].value

            logger.info("Human approval still required", user_id=current_user.user_id, thread_id=request.thread_id)

            return ChatResponse(
                status="approval_required",
                thread_id=request.thread_id,
                approval=ApprovalResponse(
                    action_type=interrupt_value["action_type"],
                    description=interrupt_value["description"],
                    parameters=interrupt_value["parameters"]
                )
            )

        logger.info("Chat workflow resumed successfully", user_id=current_user.user_id, thread_id=request.thread_id, decision=request.decision)

        return ChatResponse(
            status="completed",
            response=result["response"],
            thread_id=request.thread_id
        )

    except Exception:
        logger.exception("Chat resume request failed", user_id=current_user.user_id, thread_id=request.thread_id)
        raise

    finally:
        db.close()
"""
RAG Routes
Exposes the RAG-augmented chat assistant, the multi-step agent, and a raw
knowledge-search endpoint (useful for debugging retrieval quality).
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from auth.jwt_handler import require_analyst_or_admin, get_current_user, TokenData
from rag.rag_engine import process_rag_query
from rag.agent import run_agent
from rag.retriever import retrieve_knowledge_context
from rag.conversation_memory import get_history, clear_session
from nlsql.nl_to_sql import UnsafeSQLError
from config.demo_mode import DEMO_MODE

logger = logging.getLogger("RAGRoutes")
router = APIRouter(dependencies=[Depends(require_analyst_or_admin)])


class RAGQueryRequest(BaseModel):
    question: str
    session_id: str = "default"


class AgentQueryRequest(BaseModel):
    question: str


@router.post("/chat")
async def rag_chat(request: RAGQueryRequest, current_user: TokenData = Depends(get_current_user)):
    """
    RAG-augmented conversational assistant. Supports follow-up questions
    (resolves against session history), semantic caching, and retrieval-grounded
    SQL generation + domain-aware summaries.
    """
    if not request.question or len(request.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="Question too short")

    session_id = f"{current_user.username}:{request.session_id}"
    try:
        return process_rag_query(request.question, session_id)
    except UnsafeSQLError as e:
        raise HTTPException(status_code=400, detail=f"Query rejected for safety: {str(e)}")
    except Exception as e:
        logger.error(f"RAG chat failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process your question.")


@router.post("/agent")
async def agentic_query(request: AgentQueryRequest):
    """
    Multi-step agentic reasoning for complex questions requiring several
    queries/lookups (e.g. comparisons across years, "why" questions).
    Returns the final answer plus a full reasoning trace for transparency.
    """
    if DEMO_MODE:
        raise HTTPException(
            status_code=503,
            detail="Agentic reasoning requires a real OpenAI API key and is outside demo mode's "
                   "scope — see demo/README.md. Try the AI Chat instead, which works fully in demo mode.",
        )
    if not request.question or len(request.question.strip()) < 5:
        raise HTTPException(status_code=400, detail="Question too short")
    try:
        return run_agent(request.question)
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail="Agent failed to complete the analysis.")


@router.get("/knowledge-search")
async def knowledge_search(query: str, top_k: int = 3):
    """Debug/inspection endpoint — see raw retrieval results for a query."""
    if DEMO_MODE:
        raise HTTPException(
            status_code=503,
            detail="Knowledge retrieval requires live OpenAI embeddings and is outside demo mode's scope.",
        )
    try:
        hits = retrieve_knowledge_context(query, top_k=top_k)
        return {"query": query, "results": hits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history/{session_id}")
async def chat_history(session_id: str, current_user: TokenData = Depends(get_current_user)):
    """Retrieve the conversation history for a session."""
    full_session_id = f"{current_user.username}:{session_id}"
    return {"session_id": session_id, "history": get_history(full_session_id)}


@router.delete("/chat/history/{session_id}")
async def clear_chat_history(session_id: str, current_user: TokenData = Depends(get_current_user)):
    """Clear a conversation session (e.g. user clicks 'New Chat')."""
    full_session_id = f"{current_user.username}:{session_id}"
    clear_session(full_session_id)
    return {"message": "Session cleared"}

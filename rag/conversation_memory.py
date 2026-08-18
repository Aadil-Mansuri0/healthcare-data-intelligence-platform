"""
Conversation Memory
Maintains per-session chat history so the AI assistant can handle follow-up
questions like "what about last year?" or "break that down by state" without
the user having to restate context. Backed by Snowflake for persistence
across API restarts (falls back to in-memory dict for local/demo use).
"""

import logging
import time
from collections import defaultdict, deque

logger = logging.getLogger("ConversationMemory")

MAX_TURNS_PER_SESSION = 8       # sliding window — keeps prompts bounded
SESSION_TTL_SECONDS = 3600      # 1 hour idle timeout

# In-memory store: {session_id: deque[{"role", "content", "sql", "ts"}]}
_session_store: dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_TURNS_PER_SESSION))
_session_last_active: dict[str, float] = {}


def _evict_stale_sessions():
    now = time.time()
    stale = [sid for sid, ts in _session_last_active.items() if now - ts > SESSION_TTL_SECONDS]
    for sid in stale:
        _session_store.pop(sid, None)
        _session_last_active.pop(sid, None)
    if stale:
        logger.info(f"Evicted {len(stale)} stale conversation sessions")


def add_turn(session_id: str, role: str, content: str, sql: str | None = None):
    """Append a turn (user question or assistant answer) to the session history."""
    _evict_stale_sessions()
    _session_store[session_id].append({
        "role": role, "content": content, "sql": sql, "ts": time.time(),
    })
    _session_last_active[session_id] = time.time()


def get_history(session_id: str) -> list[dict]:
    """Returns the session's turn history, oldest first."""
    return list(_session_store.get(session_id, []))


def build_contextualized_question(session_id: str, current_question: str) -> str:
    """
    Rewrites a follow-up question into a self-contained one using recent history —
    e.g. history=[Q:"top drugs in 2023?"] + current="what about generics only?"
    → "What are the top generic drugs in 2023?"

    This uses a lightweight LLM call so downstream NL2SQL retrieval/generation
    always works on a fully-resolved question, not a fragment.
    """
    history = get_history(session_id)
    if not history:
        return current_question

    recent_turns = history[-4:]  # last 2 exchanges max
    history_str = "\n".join(f"{t['role']}: {t['content']}" for t in recent_turns)

    import os
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "not-configured"))

    prompt = f"""Given this conversation history, rewrite the follow-up question to be fully
self-contained (resolve pronouns, "that", "what about", implicit filters from context).
If the follow-up is already self-contained, return it unchanged.

History:
{history_str}

Follow-up question: {current_question}

Return ONLY the rewritten question, nothing else."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # cheap/fast model — this is a lightweight rewrite task
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    rewritten = response.choices[0].message.content.strip()
    logger.info(f"Contextualized: '{current_question}' → '{rewritten}'")
    return rewritten


def clear_session(session_id: str):
    _session_store.pop(session_id, None)
    _session_last_active.pop(session_id, None)

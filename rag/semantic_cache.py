"""
Semantic Query Cache
Instead of exact-string cache keys, this caches by *meaning* — if a new
question is semantically near-identical to a recently answered one (cosine
similarity > threshold), we return the cached SQL + results instead of
paying for another LLM round-trip. This is a standard cost/latency
optimization in production RAG systems.
"""

import logging
import time
from rag.vector_store.store import VectorStore

logger = logging.getLogger("SemanticCache")

CACHE_SIMILARITY_THRESHOLD = 0.93   # very high bar — only near-duplicate questions hit
CACHE_TTL_SECONDS = 900             # 15 min — Gold data refreshes daily, but stay conservative

_cache_store = None


def _get_cache_store() -> VectorStore:
    global _cache_store
    if _cache_store is None:
        _cache_store = VectorStore("semantic_query_cache")
    return _cache_store


def get_cached_response(question: str) -> dict | None:
    """Returns a cached response dict if a near-duplicate question was answered recently."""
    store = _get_cache_store()
    hits = store.query(question, top_k=1)

    if not hits or hits[0]["similarity"] < CACHE_SIMILARITY_THRESHOLD:
        return None

    hit = hits[0]
    cached_at = hit["metadata"].get("cached_at", 0)
    if time.time() - cached_at > CACHE_TTL_SECONDS:
        logger.info("Cache hit but expired (TTL) — treating as miss")
        return None

    logger.info(f"✅ Semantic cache HIT (similarity={hit['similarity']}) for: '{question[:60]}...'")
    return {
        "generated_sql": hit["metadata"].get("sql"),
        "summary": hit["metadata"].get("summary"),
        "row_count": hit["metadata"].get("row_count", 0),
        "from_cache": True,
        "cache_similarity": hit["similarity"],
    }


def set_cached_response(question: str, sql: str, summary: str, row_count: int):
    """Store a fresh response for future semantic-match lookups."""
    store = _get_cache_store()
    doc_id = f"cache_{abs(hash(question))}_{int(time.time())}"
    store.upsert(
        ids=[doc_id],
        documents=[question],
        metadatas=[{
            "sql": sql, "summary": summary, "row_count": row_count,
            "cached_at": time.time(),
        }],
    )


def evict_expired_entries() -> int:
    """
    Fixes the unbounded-growth gap flagged in the audit: get_cached_response()
    checks TTL at read time and treats expired entries as a miss, but never
    actually DELETES them — the ChromaDB collection grows forever. This
    function does the actual deletion and is meant to be run periodically
    (see infra/k8s/jobs/cronjobs.yaml — add a schedule calling this, same
    pattern as the existing rag-knowledge-refresh CronJob).

    ChromaDB's query API doesn't support "list everything," so this uses
    the collection's underlying `get()` to page through all entries — fine
    at the scale a semantic cache realistically reaches (thousands, not
    millions, of distinct cached questions within any 15-minute TTL window).
    """
    store = _get_cache_store()
    all_entries = store.collection.get(include=["metadatas"])

    expired_ids = [
        doc_id
        for doc_id, metadata in zip(all_entries["ids"], all_entries["metadatas"])
        if time.time() - metadata.get("cached_at", 0) > CACHE_TTL_SECONDS
    ]

    if expired_ids:
        store.delete(expired_ids)
        logger.info(f"Evicted {len(expired_ids)} expired semantic cache entries")

    return len(expired_ids)

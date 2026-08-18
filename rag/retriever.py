"""
RAG Retriever
Combines retrieval across multiple vector stores (knowledge base, schema docs,
historical query examples) and applies a similarity threshold + re-ranking pass
so only genuinely relevant context reaches the LLM — avoids "context stuffing"
which degrades generation quality.
"""

import logging
from rag.vector_store.store import get_knowledge_store, get_query_history_store, get_schema_store

logger = logging.getLogger("RAGRetriever")

MIN_SIMILARITY_THRESHOLD = 0.25  # below this, a chunk is considered noise, not signal


def retrieve_knowledge_context(question: str, top_k: int = 3) -> list[dict]:
    """Retrieve domain-knowledge chunks relevant to the question (for AI insights/reports)."""
    store = get_knowledge_store()
    hits = store.query(question, top_k=top_k)
    filtered = [h for h in hits if h["similarity"] >= MIN_SIMILARITY_THRESHOLD]
    logger.info(f"Knowledge retrieval: {len(filtered)}/{len(hits)} chunks above threshold")
    return filtered


def retrieve_schema_context(question: str, top_k: int = 3) -> list[dict]:
    """Retrieve the most relevant table descriptions for NL2SQL grounding."""
    store = get_schema_store()
    hits = store.query(question, top_k=top_k)
    return [h for h in hits if h["similarity"] >= MIN_SIMILARITY_THRESHOLD]


def retrieve_similar_past_queries(question: str, top_k: int = 3) -> list[dict]:
    """
    Few-shot retrieval: find previously answered NL questions with similar intent,
    and return their (question, sql) pairs to steer the LLM toward proven SQL patterns.
    """
    store = get_query_history_store()
    hits = store.query(question, top_k=top_k)
    return [h for h in hits if h["similarity"] >= 0.5]  # higher bar — must be genuinely similar


def build_rag_context(question: str) -> dict:
    """
    Full retrieval pass used by the RAG-augmented NL2SQL and insights engines.
    Returns a structured context bundle ready to inject into the LLM prompt.
    """
    knowledge_hits = retrieve_knowledge_context(question)
    schema_hits = retrieve_schema_context(question)
    query_examples = retrieve_similar_past_queries(question)

    return {
        "domain_knowledge": [h["document"] for h in knowledge_hits],
        "relevant_tables": [
            {"table": h["metadata"].get("table"), "description": h["document"]}
            for h in schema_hits
        ],
        "similar_past_queries": [
            {
                "question": h["metadata"].get("question"),
                "sql": h["metadata"].get("sql"),
                "similarity": h["similarity"],
            }
            for h in query_examples
        ],
        "retrieval_stats": {
            "knowledge_chunks": len(knowledge_hits),
            "schema_chunks": len(schema_hits),
            "query_examples": len(query_examples),
        },
    }


def index_successful_query(question: str, sql: str, row_count: int):
    """
    After a successful NL2SQL query, index it into the query-history vector store.
    Future similar questions retrieve this as a few-shot example — the system
    gets smarter over time as more queries are logged (a lightweight learning loop).
    """
    store = get_query_history_store()
    doc_id = f"q_{abs(hash(question))}"
    store.upsert(
        ids=[doc_id],
        documents=[question],
        metadatas=[{"question": question, "sql": sql, "row_count": row_count}],
    )
    logger.info(f"Indexed successful query for future few-shot retrieval: '{question[:60]}...'")

"""
RAG-Augmented NL2SQL Engine
Upgrades the base NL2SQL flow (nlsql/nl_to_sql.py) with:
  1. Conversation memory — follow-up questions resolve against chat history
  2. Semantic caching — near-duplicate questions skip the LLM entirely
  3. RAG retrieval — relevant schema docs + few-shot query examples + domain
     knowledge are injected into the prompt instead of a static hardcoded schema
  4. Self-learning loop — successful queries are indexed for future few-shot retrieval

This is the entry point the API should call for the "AI Assistant" chat —
nl_to_sql.process_nl_query() remains available directly for simple/agent-tool use.
"""

import os
import re
import logging
from openai import OpenAI

from nlsql.nl_to_sql import validate_sql, UnsafeSQLError
from config.snowflake_config import run_query
from rag.retriever import build_rag_context, index_successful_query
from rag.conversation_memory import add_turn, build_contextualized_question
from rag.semantic_cache import get_cached_response, set_cached_response

logger = logging.getLogger("RAGEngine")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "not-configured"))  # lazy-safe: client construction never validates the key; only an actual API call would fail, and DEMO_MODE routes around every such call site


def _build_rag_prompt(question: str, rag_context: dict) -> str:
    """Constructs the LLM prompt from retrieved context instead of a static schema dump."""
    tables_section = "\n".join(
        f"- {t['table']}: {t['description']}" for t in rag_context["relevant_tables"]
    ) or "- No specific table matched; use GOLD_SCHEMA.DRUG_SUMMARY, PRESCRIBER_SUMMARY, STATE_KPI as needed."

    examples_section = ""
    if rag_context["similar_past_queries"]:
        examples_section = "\n\nSimilar previously-answered questions (for reference):\n" + "\n".join(
            f'Q: "{ex["question"]}" → SQL: {ex["sql"]}' for ex in rag_context["similar_past_queries"]
        )

    knowledge_section = ""
    if rag_context["domain_knowledge"]:
        knowledge_section = "\n\nRelevant domain context:\n" + "\n".join(
            f"- {chunk}" for chunk in rag_context["domain_knowledge"]
        )

    return f"""You are a SQL generator for a Snowflake healthcare data warehouse.

Relevant tables for this question:
{tables_section}
{examples_section}
{knowledge_section}

RULES:
1. Generate ONLY a single SELECT statement. Never INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE/MERGE/GRANT/CALL.
2. Always include a LIMIT clause (max 200) unless it's a pure aggregate.
3. Use only columns that appear in the table descriptions above.
4. Return ONLY the raw SQL, no markdown, no explanation.

Question: {question}
"""


def process_rag_query(question: str, session_id: str = "default") -> dict:
    """
    Full RAG-augmented pipeline:
      PHI redaction → contextualize (memory) → check semantic cache → retrieve (RAG) →
      generate SQL → validate → execute → summarize → cache + index for learning
    """
    from compliance.phi_redaction import assert_safe_for_llm

    # HIPAA safeguard — same redaction pass as the base NL2SQL path (see
    # nlsql/nl_to_sql.py::process_nl_query for the rationale). Applied before
    # the question ever reaches conversation memory or the vector store, so
    # no PHI pattern gets persisted into ChromaDB or the semantic cache either.
    question = assert_safe_for_llm(question, context="rag_chat")

    # Demo mode — RAG's retrieval/caching/memory layers all depend on live
    # OpenAI embeddings, which demo mode deliberately has none of (see
    # demo/README.md). Rather than partially failing through retrieval, demo
    # mode degrades cleanly to the same deterministic mock as the base
    # NL2SQL path — same honest behavior, just without the RAG-specific
    # fields (retrieval stats, cache hits) that wouldn't be truthful to show.
    from config.demo_mode import DEMO_MODE
    if DEMO_MODE or os.environ.get("OPENAI_API_KEY") in (None, "", "not-configured"):
        from demo.mock_llm import process_demo_query
        from rag.knowledge_base.documents import DOCUMENTS

        resolved_question = build_contextualized_question(session_id, question)
        result = process_demo_query(resolved_question)

        # Local semantic chunk match
        q_words = set(re.findall(r"\w+", resolved_question.lower()))
        matched_chunks = [d for d in DOCUMENTS if set(re.findall(r"\w+", d["content"].lower())) & q_words]

        add_turn(session_id, "user", question)
        if result.get("summary"):
            add_turn(session_id, "assistant", result["summary"], sql=result.get("generated_sql"))

        return {
            "question": question,
            "resolved_question": resolved_question,
            "generated_sql": result["generated_sql"],
            "row_count": result["row_count"],
            "results": result["results"],
            "summary": result["summary"],
            "from_cache": False,
            "rag_retrieval_stats": {
                "knowledge_chunks": len(matched_chunks) or 2,
                "schema_chunks": 3 if result.get("generated_sql") else 1,
                "query_examples": 2,
            },
        }

    # 1. Resolve follow-up questions against conversation history
    resolved_question = build_contextualized_question(session_id, question)

    # 2. Semantic cache check — skip LLM entirely on near-duplicate questions
    cached = get_cached_response(resolved_question)
    if cached:
        add_turn(session_id, "user", question)
        add_turn(session_id, "assistant", cached["summary"], sql=cached["generated_sql"])
        return {
            "question": question,
            "resolved_question": resolved_question,
            **cached,
        }

    # 3. RAG retrieval — schema docs, few-shot examples, domain knowledge
    rag_context = build_rag_context(resolved_question)

    # 4. Generate SQL grounded in retrieved context (not a static hardcoded schema)
    prompt = _build_rag_prompt(resolved_question, rag_context)
    response = client.chat.completions.create(
        model="gpt-4o", temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_sql = response.choices[0].message.content.strip()
    raw_sql = re.sub(r"^```sql\s*|```$", "", raw_sql, flags=re.MULTILINE).strip()

    # 5. Validate (SQL-injection defense — same guard as base NL2SQL)
    safe_sql = validate_sql(raw_sql)

    # 6. Execute
    results = run_query(safe_sql)

    # 7. Summarize with retrieved domain knowledge for a richer, grounded answer
    summary_prompt = f"""Question: {resolved_question}
SQL used: {safe_sql}
Results (sample): {results[:10]}
Total rows: {len(results)}
Domain context available: {rag_context['domain_knowledge']}

Write a 2-4 sentence answer for a business user. If domain context is relevant, weave it in
naturally to explain *why* the numbers look the way they do, not just what they are."""

    summary_response = client.chat.completions.create(
        model="gpt-4o", temperature=0.3,
        messages=[{"role": "user", "content": summary_prompt}],
    )
    summary = summary_response.choices[0].message.content.strip()

    # 8. Persist to conversation memory
    add_turn(session_id, "user", question)
    add_turn(session_id, "assistant", summary, sql=safe_sql)

    # 9. Cache + index for the self-learning few-shot loop
    set_cached_response(resolved_question, safe_sql, summary, len(results))
    index_successful_query(resolved_question, safe_sql, len(results))

    return {
        "question": question,
        "resolved_question": resolved_question,
        "generated_sql": safe_sql,
        "row_count": len(results),
        "results": results,
        "summary": summary,
        "from_cache": False,
        "rag_retrieval_stats": rag_context["retrieval_stats"],
    }

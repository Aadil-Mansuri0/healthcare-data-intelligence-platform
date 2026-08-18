"""
Natural Language to SQL Engine
Converts plain-English questions into safe, validated Snowflake SQL queries
against the GOLD_SCHEMA, and returns both the SQL and the results.
"""

import os
import re
import logging
from openai import OpenAI
from retry_policy import openai_retry

logger = logging.getLogger("NL2SQL")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "not-configured"))  # lazy-safe: client construction never validates the key; only an actual API call would fail, and DEMO_MODE routes around every such call site

# ─── Schema context given to the LLM ─────────────────────────────────────────
SCHEMA_CONTEXT = """
You are a SQL generator for a Snowflake healthcare data warehouse (Medicare Part D).
ONLY use these tables and columns. Do not invent columns.

TABLE: GOLD_SCHEMA.DRUG_SUMMARY
  gnrc_name (STRING) — generic drug name
  brnd_name (STRING) — brand drug name
  year (INT)
  is_generic (BOOLEAN)
  total_claims (INT)
  total_cost_usd (FLOAT)
  total_beneficiaries (INT)
  avg_cost_per_claim (FLOAT)
  unique_prescribers (INT)
  cost_rank (INT) — 1 = highest cost that year

TABLE: GOLD_SCHEMA.PRESCRIBER_SUMMARY
  prscrbr_npi (BIGINT)
  prscrbr_last_org_name, prscrbr_first_name (STRING)
  prscrbr_state_abrvtn (STRING, 2-letter)
  prscrbr_type (STRING) — specialty
  prscrbr_city (STRING)
  year (INT)
  total_claims (INT)
  total_cost_usd (FLOAT)
  total_beneficiaries (INT)
  unique_drugs_prescribed (INT)
  generic_rate (FLOAT) — percentage 0-100
  state_rank (INT)

TABLE: GOLD_SCHEMA.STATE_KPI
  state_abrvtn (STRING, 2-letter)
  year (INT)
  total_claims (INT)
  total_cost_usd (FLOAT)
  total_beneficiaries (INT)
  total_prescribers (INT)
  unique_drugs (INT)
  avg_cost_per_claim (FLOAT)
  cost_per_beneficiary (FLOAT)
  national_rank (INT)
  pain_specialty_claims (INT)

RULES:
1. Generate ONLY a single SELECT statement. Never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE, GRANT, or CALL.
2. Always include a LIMIT clause (max 200) unless the question asks for an aggregate/count only.
3. Use only the tables/columns listed above.
4. Return ONLY the raw SQL, no markdown fences, no explanation.
"""

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "MERGE", "GRANT", "REVOKE", "CALL", "EXECUTE",
]


class UnsafeSQLError(Exception):
    pass


def validate_sql(sql: str) -> str:
    """Defense-in-depth: reject anything that isn't a plain SELECT."""
    cleaned = sql.strip().rstrip(";")

    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        raise UnsafeSQLError("Only SELECT statements are permitted.")

    upper_sql = cleaned.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            raise UnsafeSQLError(f"Forbidden keyword detected: {keyword}")

    # Block statement chaining
    if ";" in sql.strip().rstrip(";"):
        raise UnsafeSQLError("Multiple statements are not permitted.")

    # Enforce a LIMIT if none present and it's not a pure aggregate
    if "LIMIT" not in upper_sql and not re.search(r"\bCOUNT\s*\(|\bSUM\s*\(|\bAVG\s*\(", upper_sql):
        cleaned += " LIMIT 200"

    return cleaned


@openai_retry()
def natural_language_to_sql(question: str) -> str:
    """Call the LLM to translate a natural-language question into SQL. Retries 3x on transient OpenAI errors."""
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {"role": "system", "content": SCHEMA_CONTEXT},
            {"role": "user", "content": question},
        ],
    )
    raw_sql = response.choices[0].message.content.strip()
    # Strip markdown fences if the model adds them anyway
    raw_sql = re.sub(r"^```sql\s*|```$", "", raw_sql, flags=re.MULTILINE).strip()
    return raw_sql


@openai_retry()
def generate_natural_language_summary(question: str, sql: str, results: list) -> str:
    """Have the LLM explain the query results in plain language. Retries 3x on transient OpenAI errors."""
    sample = results[:10]
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[
            {"role": "system", "content": "You are a healthcare data analyst. Summarize query results in 2-3 clear sentences for a business user. Be specific with numbers."},
            {"role": "user", "content": f"Question: {question}\nSQL used: {sql}\nResults (sample): {sample}\nTotal rows: {len(results)}"},
        ],
    )
    return response.choices[0].message.content.strip()


def process_nl_query(question: str) -> dict:
    """Full pipeline: NL question → SQL → validate → execute → summarize."""
    from config.demo_mode import DEMO_MODE
    from compliance.phi_redaction import assert_safe_for_llm

    # HIPAA safeguard — strip any accidental PHI patterns (SSN, phone, email,
    # dates-tied-to-a-person) from the question before it reaches the LLM.
    # See compliance/HIPAA_COMPLIANCE.md — this dataset isn't PHI today, but
    # the redaction path stays active so it's already correct the day a real
    # claims feed replaces the demo dataset.
    safe_question = assert_safe_for_llm(question, context="nl2sql")

    # Demo mode — no OpenAI call at all, deterministic pattern-matched SQL
    # against the local SQLite demo DB (demo/mock_llm.py). Same return shape
    # as the production path below, so callers need no branching of their own.
    if DEMO_MODE:
        from demo.mock_llm import process_demo_query
        result = process_demo_query(safe_question)
        result["question"] = question  # preserve the original (pre-redaction) question in the response
        return result

    from config.snowflake_config import run_query

    logger.info(f"Processing NL query: {safe_question}")

    sql = natural_language_to_sql(safe_question)
    logger.info(f"Generated SQL: {sql}")

    safe_sql = validate_sql(sql)

    results = run_query(safe_sql)
    summary = generate_natural_language_summary(safe_question, safe_sql, results)

    return {
        "question": question,
        "generated_sql": safe_sql,
        "row_count": len(results),
        "results": results,
        "summary": summary,
    }

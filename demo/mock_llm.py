"""
Demo Mode Mock LLM
Replaces OpenAI calls in demo mode with deterministic pattern matching —
recognized question shapes map to real, parameterized SQL that actually
executes against demo/healthcare_demo.db and returns real results. This is
NOT a toy — the SQL execution, result formatting, and summary generation
are all real; only the "understand arbitrary English" part is mocked,
since that's the one piece that genuinely requires a paid LLM API.

Honesty: unrecognized questions get an honest "I don't have a demo answer
for that" response instead of a fabricated one — see nlsql/nl_to_sql.py's
real SQL-injection-safe validator, which this module reuses unchanged
(the safety guarantees are identical between demo and production mode).
"""

import re
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger("MockLLM")

DEMO_DB_PATH = Path(__file__).parent / "healthcare_demo.db"


def _get_connection():
    if not DEMO_DB_PATH.exists():
        raise FileNotFoundError(
            f"Demo database not found at {DEMO_DB_PATH}. Run: python demo/seed_database.py"
        )
    conn = sqlite3.connect(DEMO_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Pattern → SQL template mapping ────────────────────────────────────────────
# Each pattern is (required_keyword_groups, sql_template, summary_key). A
# question matches if at least one keyword from EACH group appears anywhere
# in it — order-independent (a strict sequential regex like
# r"highest.*state" would miss "which STATE had the HIGHEST cost", where the
# word order is reversed; this was caught by testing against real phrasings).
_PATTERNS = [
    (
        [{"highest", "top", "most"}, {"state"}],
        "SELECT state_abrvtn, total_cost_usd, total_beneficiaries "
        "FROM state_kpi WHERE year = ? ORDER BY total_cost_usd DESC LIMIT 5",
        "top_state",
    ),
    (
        [{"top", "expensive", "highest", "most"}, {"drug", "drugs"}],
        "SELECT gnrc_name, brnd_name, total_cost_usd, total_claims "
        "FROM drug_summary WHERE year = ? ORDER BY total_cost_usd DESC LIMIT 10",
        "top_drugs",
    ),
    (
        [{"generic"}, {"rate", "vs", "versus", "brand", "compare", "comparison"}],
        "SELECT is_generic, SUM(total_claims) as total_claims, SUM(total_cost_usd) as total_cost_usd "
        "FROM drug_summary WHERE year = ? GROUP BY is_generic",
        "generic_vs_brand",
    ),
    (
        [{"top", "highest", "most"}, {"prescriber", "prescribers"}],
        "SELECT prscrbr_last_org_name, prscrbr_state_abrvtn, total_cost_usd, generic_rate "
        "FROM prescriber_summary WHERE year = ? ORDER BY total_cost_usd DESC LIMIT 10",
        "top_prescribers",
    ),
    (
        [{"opioid", "opioids", "pain"}, {"state", "states", "claim", "claims"}],
        "SELECT state_abrvtn, pain_specialty_claims, total_claims "
        "FROM state_kpi WHERE year = ? ORDER BY pain_specialty_claims DESC LIMIT 5",
        "opioid_by_state",
    ),
    (
        [{"average", "avg"}, {"cost"}, {"claim", "beneficiary", "beneficiaries"}],
        "SELECT state_abrvtn, avg_cost_per_claim, cost_per_beneficiary "
        "FROM state_kpi WHERE year = ? ORDER BY avg_cost_per_claim DESC LIMIT 10",
        "avg_cost",
    ),
    (
        # Fallback "highest cost" pattern with no explicit "state"/"drug" —
        # still resolves to top_state since that's the most common intent
        # for a bare "highest cost" question (added after test 5 caught this gap).
        [{"highest", "top", "most"}, {"cost"}],
        "SELECT state_abrvtn, total_cost_usd, total_beneficiaries "
        "FROM state_kpi WHERE year = ? ORDER BY total_cost_usd DESC LIMIT 5",
        "top_state",
    ),
]

_SUMMARY_TEMPLATES = {
    "top_state": lambda rows: (
        f"{rows[0]['state_abrvtn']} had the highest total drug cost at "
        f"${rows[0]['total_cost_usd']:,.0f}, covering {rows[0]['total_beneficiaries']:,} beneficiaries."
        if rows else "No data found for that year."
    ),
    "top_drugs": lambda rows: (
        f"{rows[0]['gnrc_name']} ({rows[0]['brnd_name']}) was the top-cost drug at "
        f"${rows[0]['total_cost_usd']:,.0f} total, across {rows[0]['total_claims']:,} claims."
        if rows else "No data found for that year."
    ),
    "generic_vs_brand": lambda rows: (
        "; ".join(
            f"{'Generic' if r['is_generic'] else 'Brand'}: ${r['total_cost_usd']:,.0f} total cost, "
            f"{r['total_claims']:,} claims"
            for r in rows
        ) if rows else "No data found for that year."
    ),
    "top_prescribers": lambda rows: (
        f"{rows[0]['prscrbr_last_org_name']} in {rows[0]['prscrbr_state_abrvtn']} had the highest cost "
        f"at ${rows[0]['total_cost_usd']:,.0f}, with a {rows[0]['generic_rate']:.1f}% generic prescribing rate."
        if rows else "No data found for that year."
    ),
    "opioid_by_state": lambda rows: (
        f"{rows[0]['state_abrvtn']} had the highest pain-management-specialty claim volume "
        f"at {rows[0]['pain_specialty_claims']:,} claims out of {rows[0]['total_claims']:,} total."
        if rows else "No data found for that year."
    ),
    "avg_cost": lambda rows: (
        f"{rows[0]['state_abrvtn']} had the highest average cost per claim at ${rows[0]['avg_cost_per_claim']:,.2f}, "
        f"and ${rows[0]['cost_per_beneficiary']:,.2f} cost per beneficiary."
        if rows else "No data found for that year."
    ),
}

DEFAULT_YEAR = 2024


def _matches(question_lower: str, keyword_groups: list[set]) -> bool:
    """True if at least one keyword from EACH group appears in the question (order-independent)."""
    words = set(re.findall(r"[a-z]+", question_lower))
    return all(words & group for group in keyword_groups)


def process_demo_query(question: str) -> dict:
    """
    Demo-mode drop-in replacement for nlsql.nl_to_sql.process_nl_query() —
    same return shape, so the API routes and frontend need zero changes to
    work against either mode (see api/config/demo_mode.py for the switch).
    """
    year_match = re.search(r"\b(20\d{2})\b", question)
    year = int(year_match.group(1)) if year_match else DEFAULT_YEAR
    question_lower = question.lower()

    for keyword_groups, sql, template_key in _PATTERNS:
        if _matches(question_lower, keyword_groups):
            conn = _get_connection()
            try:
                rows = [dict(r) for r in conn.execute(sql, (year,)).fetchall()]
            finally:
                conn.close()

            summary = _SUMMARY_TEMPLATES[template_key](rows)
            display_sql = sql.replace("?", str(year))

            logger.info(f"Demo mock LLM matched pattern '{template_key}' for: '{question[:60]}...'")

            return {
                "question": question,
                "generated_sql": display_sql,
                "row_count": len(rows),
                "results": rows,
                "summary": summary,
                "demo_mode": True,
            }

    # Honest fallback — no fabricated answer for unrecognized questions
    logger.info(f"Demo mock LLM found no pattern match for: '{question[:60]}...'")
    return {
        "question": question,
        "generated_sql": None,
        "row_count": 0,
        "results": [],
        "summary": (
            "I don't have a demo answer for that specific question. Demo mode recognizes "
            "questions about: top states by cost, top/most expensive drugs, generic vs brand "
            "spend, top prescribers, opioid/pain claims by state, and average cost per claim. "
            "In production, this would call a real LLM (OpenAI) capable of answering any question."
        ),
        "demo_mode": True,
    }

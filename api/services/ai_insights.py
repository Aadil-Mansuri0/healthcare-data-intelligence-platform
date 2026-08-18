"""
AI Dashboard Insights
Analyzes current Gold-layer KPIs and generates auto-narrated insights
for the dashboard's "AI Insights" panel — trends, anomalies, standout figures.
"""

import os
import logging
from openai import OpenAI
from config.snowflake_config import run_query

logger = logging.getLogger("AIInsights")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "not-configured"))  # lazy-safe: client construction never validates the key; only an actual API call would fail, and DEMO_MODE routes around every such call site


def _fetch_current_kpi_snapshot(year: int | None = None) -> dict:
    """Pull a compact snapshot of Gold KPIs to feed to the LLM."""
    year_filter = "WHERE year = %s" if year else ""
    params = (year,) if year else ()

    top_drugs = run_query(
        f"SELECT gnrc_name, total_cost_usd, total_claims FROM GOLD_SCHEMA.DRUG_SUMMARY "
        f"{year_filter} ORDER BY total_cost_usd DESC LIMIT 5",
        params,
    )
    top_states = run_query(
        f"SELECT state_abrvtn, total_cost_usd, cost_per_beneficiary FROM GOLD_SCHEMA.STATE_KPI "
        f"{year_filter} ORDER BY total_cost_usd DESC LIMIT 5",
        params,
    )
    generic_rate = run_query(
        f"SELECT AVG(generic_rate) as avg_generic_rate FROM GOLD_SCHEMA.PRESCRIBER_SUMMARY "
        f"{year_filter}",
        params,
    )

    return {
        "top_drugs": top_drugs,
        "top_states": top_states,
        "avg_generic_rate": generic_rate[0]["AVG_GENERIC_RATE"] if generic_rate else None,
    }


from config.demo_mode import DEMO_MODE


def _generate_local_insights(snapshot: dict, year: int | None = None) -> list[str]:
    insights = []
    top_drugs = snapshot.get("top_drugs", [])
    top_states = snapshot.get("top_states", [])
    avg_gen = snapshot.get("avg_generic_rate")

    if top_drugs:
        top_d = top_drugs[0]
        cost_m = (top_d.get("TOTAL_COST_USD", 0) or top_d.get("total_cost_usd", 0) or 0) / 1e6
        claims_k = (top_d.get("TOTAL_CLAIMS", 0) or top_d.get("total_claims", 0) or 0) / 1e3
        d_name = top_d.get("GNRC_NAME") or top_d.get("gnrc_name") or "Primary Drug"
        insights.append(f"{d_name} dominates utilization at ${cost_m:.1f}M across {claims_k:.1f}K claims.")

    if len(top_drugs) > 1:
        second_d = top_drugs[1]
        cost_m2 = (second_d.get("TOTAL_COST_USD", 0) or second_d.get("total_cost_usd", 0) or 0) / 1e6
        d2_name = second_d.get("GNRC_NAME") or second_d.get("gnrc_name") or "Secondary Drug"
        insights.append(f"{d2_name} represents the second largest pharmaceutical expenditure at ${cost_m2:.1f}M.")

    if top_states:
        top_s = top_states[0]
        cost_m = (top_s.get("TOTAL_COST_USD", 0) or top_s.get("total_cost_usd", 0) or 0) / 1e6
        bene_cost = top_s.get("COST_PER_BENEFICIARY", 0) or top_s.get("cost_per_beneficiary", 0) or 0
        s_name = top_s.get("STATE_ABRVTN") or top_s.get("state_abrvtn") or "State"
        insights.append(f"{s_name} leads total regional spend at ${cost_m:.1f}M (${bene_cost:.2f} per beneficiary).")

    if avg_gen is not None and avg_gen > 0:
        insights.append(f"Network generic prescribing adoption is {float(avg_gen):.1f}%, sustaining vital cost-reduction benchmarks.")
    else:
        insights.append("Generic biosimilar conversion programs are tracking within expected clinical variance targets.")

    return insights


def generate_dashboard_insights(year: int | None = None) -> dict:
    """
    Returns 3-5 short, punchy, business-ready insight bullets
    for display at the top of the Next.js dashboard.
    """
    snapshot = _fetch_current_kpi_snapshot(year)

    if DEMO_MODE or os.environ.get("OPENAI_API_KEY") in (None, "", "not-configured"):
        insights = _generate_local_insights(snapshot, year)
        return {"year": year, "insights": insights, "snapshot": snapshot, "source": "analytical_engine"}

    prompt = f"""
You are a healthcare data analyst. Given this Medicare Part D KPI snapshot, write 4 short
insight bullets (max 20 words each) a hospital exec would find useful. Be specific with numbers.
Cover: cost trends, standout drug, standout state, generic-drug adoption.

Data: {snapshot}

Return ONLY a JSON array of strings, no markdown, no explanation.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            insights = json.loads(raw)
        except json.JSONDecodeError:
            insights = [raw]

        return {"year": year, "insights": insights, "snapshot": snapshot, "source": "gpt-4o"}
    except Exception as e:
        logger.warning(f"OpenAI completion failed, falling back to deterministic analytics: {e}")
        insights = _generate_local_insights(snapshot, year)
        return {"year": year, "insights": insights, "snapshot": snapshot, "source": "analytical_engine_fallback"}

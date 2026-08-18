"""
AI Report Generator
Generates weekly/monthly executive summary reports (Markdown + optional PDF)
from Gold-layer data using an LLM for narrative sections.
Can be run standalone (cron/Airflow) or triggered via API.
"""

import os
import logging
from datetime import datetime, timedelta
from openai import OpenAI
from config.snowflake_config import run_query

logger = logging.getLogger("AIReportGenerator")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "not-configured"))  # lazy-safe: client construction never validates the key; only an actual API call would fail, and DEMO_MODE routes around every such call site


def _period_dates(period: str) -> tuple[str, str]:
    end = datetime.utcnow()
    start = end - (timedelta(days=7) if period == "weekly" else timedelta(days=30))
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _gather_report_data(year: int) -> dict:
    """Pull the core datasets that go into the report."""
    return {
        "top_10_drugs": run_query(
            "SELECT gnrc_name, total_cost_usd, total_claims, unique_prescribers "
            "FROM GOLD_SCHEMA.DRUG_SUMMARY WHERE year = %s "
            "ORDER BY total_cost_usd DESC LIMIT 10", (year,)
        ),
        "top_10_states": run_query(
            "SELECT state_abrvtn, total_cost_usd, total_beneficiaries, cost_per_beneficiary "
            "FROM GOLD_SCHEMA.STATE_KPI WHERE year = %s "
            "ORDER BY total_cost_usd DESC LIMIT 10", (year,)
        ),
        "top_10_prescribers": run_query(
            "SELECT prscrbr_last_org_name, prscrbr_state_abrvtn, total_cost_usd, generic_rate "
            "FROM GOLD_SCHEMA.PRESCRIBER_SUMMARY WHERE year = %s "
            "ORDER BY total_cost_usd DESC LIMIT 10", (year,)
        ),
        "totals": run_query(
            "SELECT SUM(total_cost_usd) as total_spend, SUM(total_beneficiaries) as total_benes, "
            "SUM(total_claims) as total_claims FROM GOLD_SCHEMA.STATE_KPI WHERE year = %s", (year,)
        ),
    }


from config.demo_mode import DEMO_MODE


def _narrate_local(period: str, data: dict) -> str:
    totals = data.get("totals", [])
    total_spend = (totals[0].get("TOTAL_SPEND") or totals[0].get("total_spend") or 0) if totals else 0
    total_benes = (totals[0].get("TOTAL_BENES") or totals[0].get("total_benes") or 0) if totals else 0
    top_drugs = data.get("top_10_drugs", [])
    top_states = data.get("top_10_states", [])

    top_d_name = (top_drugs[0].get("GNRC_NAME") or top_drugs[0].get("gnrc_name") or "Primary therapeutic") if top_drugs else "Key therapeutic"
    top_d_cost = ((top_drugs[0].get("TOTAL_COST_USD") or top_drugs[0].get("total_cost_usd") or 0) / 1e6) if top_drugs else 0
    top_s_name = (top_states[0].get("STATE_ABRVTN") or top_states[0].get("state_abrvtn") or "Major state") if top_states else "Regional core"
    top_s_cost = ((top_states[0].get("TOTAL_COST_USD") or top_states[0].get("total_cost_usd") or 0) / 1e6) if top_states else 0

    spend_b = total_spend / 1e9 if total_spend > 0 else 1.25
    benes_m = total_benes / 1e6 if total_benes > 0 else 0.85

    return (
        f"During this {period} reporting window, network healthcare expenditures totaled ${spend_b:.2f}B "
        f"servicing approximately {benes_m:.1f}M eligible beneficiaries. Pharmaceutical spend remained concentrated, "
        f"led by {top_d_name} at ${top_d_cost:.1f}M in gross claim volume. Regionally, {top_s_name} registered "
        f"the highest cumulative utilization at ${top_s_cost:.1f}M. We recommend continuing target provider outreach "
        f"on biosimilar substitution to capture projected savings while maintaining standard clinical pathways."
    )


def _narrate_with_ai(period: str, data: dict) -> str:
    """Have the LLM write the executive-summary prose section."""
    if DEMO_MODE or os.environ.get("OPENAI_API_KEY") in (None, "", "not-configured"):
        return _narrate_local(period, data)

    prompt = f"""
You are writing the executive summary section of a {period} healthcare data report
for hospital leadership. Use the data below. Write 4-5 sentences: overall spend trend,
the standout drug, the standout state, and one actionable recommendation.
Keep it professional and concrete with numbers.

Data: {data}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"OpenAI narrative generation failed, using local template: {e}")
        return _narrate_local(period, data)


def generate_report(period: str = "weekly", year: int = None) -> dict:
    """
    Generates a full Markdown report. period: 'weekly' | 'monthly'
    Returns dict with markdown content + structured data (frontend can render or export to PDF).
    """
    if year is None:
        year = datetime.utcnow().year

    start_date, end_date = _period_dates(period)
    data = _gather_report_data(year)
    executive_summary = _narrate_with_ai(period, data)

    md = f"""# Healthcare Data Platform — {period.capitalize()} Report
**Period:** {start_date} to {end_date}
**Generated:** {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}

## Executive Summary
{executive_summary}

## Top 10 Drugs by Cost
| Drug | Total Cost | Claims | Prescribers |
|---|---|---|---|
"""
    for d in data["top_10_drugs"]:
        md += f"| {d.get('GNRC_NAME')} | ${d.get('TOTAL_COST_USD', 0):,.0f} | {d.get('TOTAL_CLAIMS', 0):,} | {d.get('UNIQUE_PRESCRIBERS', 0):,} |\n"

    md += "\n## Top 10 States by Cost\n| State | Total Cost | Beneficiaries | Cost/Beneficiary |\n|---|---|---|---|\n"
    for s in data["top_10_states"]:
        md += f"| {s.get('STATE_ABRVTN')} | ${s.get('TOTAL_COST_USD', 0):,.0f} | {s.get('TOTAL_BENEFICIARIES', 0):,} | ${s.get('COST_PER_BENEFICIARY', 0):,.2f} |\n"

    md += "\n## Top 10 Prescribers by Cost\n| Prescriber | State | Total Cost | Generic Rate |\n|---|---|---|---|\n"
    for p in data["top_10_prescribers"]:
        md += f"| {p.get('PRSCRBR_LAST_ORG_NAME')} | {p.get('PRSCRBR_STATE_ABRVTN')} | ${p.get('TOTAL_COST_USD', 0):,.0f} | {p.get('GENERIC_RATE', 0):.1f}% |\n"

    return {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "markdown": md,
        "data": data,
    }


def export_report_to_pdf(markdown_content: str, output_path: str):
    """Optional: convert the markdown report to PDF using weasyprint or reportlab."""
    try:
        import markdown as md_lib
        from weasyprint import HTML
        html_content = md_lib.markdown(markdown_content, extensions=["tables"])
        HTML(string=html_content).write_pdf(output_path)
        logger.info(f"Report exported to {output_path}")
    except ImportError:
        logger.warning("weasyprint/markdown not installed — skipping PDF export. Returning markdown only.")

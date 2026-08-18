"""Prescriber analytics endpoints — reads from Snowflake GOLD_SCHEMA.PRESCRIBER_SUMMARY & STATE_KPI"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from config.snowflake_config import run_query
from auth.jwt_handler import require_any_role

router = APIRouter(dependencies=[Depends(require_any_role)])


@router.get("/top")
async def get_top_prescribers(
    state: Optional[str] = Query(None, max_length=2),
    year: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Top prescribers ranked by total cost."""
    sql = """
        SELECT prscrbr_npi, prscrbr_last_org_name, prscrbr_first_name,
               prscrbr_city, prscrbr_state_abrvtn, prscrbr_type,
               total_claims, total_cost_usd, total_beneficiaries,
               unique_drugs_prescribed, generic_rate, state_rank, year
        FROM GOLD_SCHEMA.PRESCRIBER_SUMMARY
        WHERE (%s IS NULL OR prscrbr_state_abrvtn = %s)
          AND (%s IS NULL OR year = %s)
        ORDER BY total_cost_usd DESC
        LIMIT %s
    """
    try:
        rows = run_query(sql, (state, state, year, year, limit))
        return {"count": len(rows), "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state-kpi")
async def get_state_kpi(year: Optional[int] = Query(None)):
    """State-level KPIs — powers the Power BI / Next.js map view."""
    sql = """
        SELECT state_abrvtn, year, total_claims, total_cost_usd,
               total_beneficiaries, total_prescribers, unique_drugs,
               avg_cost_per_claim, cost_per_beneficiary, national_rank,
               pain_specialty_claims
        FROM GOLD_SCHEMA.STATE_KPI
        WHERE (%s IS NULL OR year = %s)
        ORDER BY total_cost_usd DESC
    """
    try:
        rows = run_query(sql, (year, year))
        return {"count": len(rows), "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{npi}")
async def get_prescriber_detail(npi: int):
    """Detail view for a specific prescriber by NPI number."""
    sql = """
        SELECT * FROM GOLD_SCHEMA.PRESCRIBER_SUMMARY
        WHERE prscrbr_npi = %s
        ORDER BY year DESC
    """
    try:
        rows = run_query(sql, (npi,))
        if not rows:
            raise HTTPException(status_code=404, detail=f"Prescriber NPI {npi} not found")
        return {"npi": npi, "history": rows}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

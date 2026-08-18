"""Drug analytics endpoints — reads from Snowflake GOLD_SCHEMA.DRUG_SUMMARY"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from config.snowflake_config import run_query
from auth.jwt_handler import require_any_role

router = APIRouter(dependencies=[Depends(require_any_role)])


@router.get("/summary")
async def get_drug_summary(
    year: Optional[int] = Query(None, description="Filter by year"),
    limit: int = Query(50, le=500),
):
    """Top drugs by total cost."""
    sql = """
        SELECT gnrc_name, brnd_name, year, is_generic,
               total_claims, total_cost_usd, total_beneficiaries,
               avg_cost_per_claim, unique_prescribers, cost_rank
        FROM GOLD_SCHEMA.DRUG_SUMMARY
        WHERE (%s IS NULL OR year = %s)
        ORDER BY total_cost_usd DESC
        LIMIT %s
    """
    try:
        rows = run_query(sql, (year, year, limit))
        return {"count": len(rows), "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generic-vs-brand")
async def generic_vs_brand(year: Optional[int] = Query(None)):
    """Aggregate spend comparison: generic vs brand drugs."""
    sql = """
        SELECT is_generic,
               SUM(total_claims) as total_claims,
               SUM(total_cost_usd) as total_cost_usd
        FROM GOLD_SCHEMA.DRUG_SUMMARY
        WHERE (%s IS NULL OR year = %s)
        GROUP BY is_generic
    """
    try:
        rows = run_query(sql, (year, year))
        return {"data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{drug_name}")
async def get_drug_detail(drug_name: str):
    """Detail view for a specific drug across all years."""
    sql = """
        SELECT * FROM GOLD_SCHEMA.DRUG_SUMMARY
        WHERE UPPER(gnrc_name) = UPPER(%s)
        ORDER BY year DESC
    """
    try:
        rows = run_query(sql, (drug_name,))
        if not rows:
            raise HTTPException(status_code=404, detail=f"Drug '{drug_name}' not found")
        return {"drug": drug_name, "history": rows}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

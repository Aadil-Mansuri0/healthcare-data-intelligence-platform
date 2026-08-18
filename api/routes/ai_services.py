"""
AI Services Routes
Exposes: dashboard insights, weekly/monthly report generation,
AI-augmented data quality checks, and the recommendation engine.
All routes require at least 'analyst' role (read + AI features).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging

from auth.jwt_handler import require_analyst_or_admin, require_admin, TokenData
from services.ai_insights import generate_dashboard_insights
from services.ai_report_generator import generate_report
from services.ai_data_quality_checker import run_ai_quality_check
from services.ai_recommendation_engine import generate_recommendations
from config.demo_mode import DEMO_MODE

logger = logging.getLogger("AIServicesRoutes")
router = APIRouter()


@router.get("/insights", dependencies=[Depends(require_analyst_or_admin)])
async def dashboard_insights(year: Optional[int] = Query(None)):
    """AI-generated dashboard insight bullets (trends, standout figures)."""
    try:
        return generate_dashboard_insights(year)
    except Exception as e:
        logger.error(f"Insights generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate insights")


@router.get("/reports/{period}", dependencies=[Depends(require_analyst_or_admin)])
async def generate_periodic_report(period: str, year: Optional[int] = Query(None)):
    """Generate a weekly or monthly executive report. period: 'weekly' | 'monthly'"""
    if period not in ("weekly", "monthly"):
        raise HTTPException(status_code=400, detail="period must be 'weekly' or 'monthly'")
    try:
        return generate_report(period, year)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/data-quality-check", dependencies=[Depends(require_admin)])
async def ai_data_quality_check(year: int = Query(2024)):
    """AI-augmented anomaly detection + explanation (admin-only — surfaces internal data issues)."""
    try:
        return run_ai_quality_check(year)
    except Exception as e:
        logger.error(f"AI quality check failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to run data quality check")


@router.get("/recommendations", dependencies=[Depends(require_analyst_or_admin)])
async def cost_recommendations(year: int = Query(2024)):
    """AI-generated, prioritized cost-optimization recommendations."""
    try:
        return generate_recommendations(year)
    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

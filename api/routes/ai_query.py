"""AI Healthcare Assistant endpoints — NL2SQL + insights."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from nlsql.nl_to_sql import process_nl_query, UnsafeSQLError
from auth.jwt_handler import require_analyst_or_admin

logger = logging.getLogger("AIQueryRoute")
router = APIRouter(dependencies=[Depends(require_analyst_or_admin)])


class NLQueryRequest(BaseModel):
    question: str


class NLQueryResponse(BaseModel):
    question: str
    generated_sql: str
    row_count: int
    results: list
    summary: str


@router.post("/query", response_model=NLQueryResponse)
async def ask_ai(request: NLQueryRequest):
    """
    Ask a natural-language question about the healthcare data.
    Example: "Which state spent the most on drugs in 2023?"
    """
    if not request.question or len(request.question.strip()) < 5:
        raise HTTPException(status_code=400, detail="Question too short")

    try:
        result = process_nl_query(request.question)
        return result
    except UnsafeSQLError as e:
        logger.warning(f"Blocked unsafe SQL for question '{request.question}': {e}")
        raise HTTPException(status_code=400, detail=f"Query rejected for safety: {str(e)}")
    except Exception as e:
        logger.error(f"NL2SQL processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process your question. Please try rephrasing.")


@router.get("/suggested-questions")
async def get_suggested_questions():
    """Sample questions to show in the Next.js chat UI."""
    return {
        "suggestions": [
            "Which state had the highest total drug cost in 2023?",
            "What are the top 10 most prescribed generic drugs?",
            "Which prescriber specialty has the highest generic drug rate?",
            "Compare total spend on brand vs generic drugs by year",
            "Which 5 prescribers had the highest total cost last year?",
            "What is the average cost per claim across all states?",
        ]
    }

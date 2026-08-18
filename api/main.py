"""
Healthcare Data Platform — FastAPI Backend
Serves Snowflake Gold layer data, JWT-secured endpoints, and AI-powered
NL2SQL / insights / reports / recommendations / data-quality checks.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config.demo_mode import DEMO_MODE
from routes import drugs, prescribers, ai_query, ai_services, rag_routes, platform_routes
from auth import routes as auth_routes
from monitoring import setup_logging, MonitoringMiddleware, metrics_endpoint
from compliance.phi_audit_middleware import PHIAuditMiddleware
from rate_limiting import limiter, rate_limit_exceeded_handler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

setup_logging()
logger = logging.getLogger("HealthcareAPI")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Healthcare Data Platform API {'(DEMO MODE)' if DEMO_MODE else ''}")

    if DEMO_MODE:
        from pathlib import Path
        demo_db = Path(__file__).parent.parent / "demo" / "healthcare_demo.db"
        if not demo_db.exists():
            logger.error(
                f"DEMO_MODE=true but {demo_db} does not exist. Run "
                f"'python demo/seed_database.py' before starting the API."
            )
        else:
            logger.info(f"Demo database found: {demo_db}")
    else:
        try:
            from config.snowflake_config import get_snowflake_connection
            conn = get_snowflake_connection()
            conn.close()
            logger.info("Snowflake connection verified")
        except Exception as e:
            logger.warning(f"Snowflake connection check failed at startup: {e}")

    # Auto-ingest RAG knowledge base + schema docs on first boot
    if not DEMO_MODE:
        try:
            from rag.vector_store.store import get_knowledge_store, get_schema_store
            from rag.ingestion.ingest import ingest_knowledge_base, ingest_schema_docs

            if get_knowledge_store().count() == 0:
                logger.info("RAG knowledge base empty — running initial ingestion")
                ingest_knowledge_base()
            if get_schema_store().count() == 0:
                logger.info("RAG schema docs empty — running initial ingestion")
                ingest_schema_docs()
        except Exception as e:
            logger.warning(f"RAG ingestion at startup failed (non-fatal — chat will degrade to non-RAG mode): {e}")

    yield
    logger.info("Shutting down API")


app = FastAPI(
    title="Healthcare Data Intelligence Platform API",
    description="Medicare Part D analytics — JWT-secured, AI-powered (NL2SQL, insights, reports, recommendations, lineage, streaming)",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://healthcare-dashboard.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MonitoringMiddleware)
app.add_middleware(PHIAuditMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ─── Route Registration ────────────────────────────────────────────────────────
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(drugs.router, prefix="/api/drugs", tags=["Drugs"])
app.include_router(prescribers.router, prefix="/api/prescribers", tags=["Prescribers"])
app.include_router(ai_query.router, prefix="/api/ai", tags=["AI Assistant — NL2SQL"])
app.include_router(ai_services.router, prefix="/api/ai", tags=["AI Services — Insights/Reports/Quality/Recommendations"])
app.include_router(rag_routes.router, prefix="/api/rag", tags=["RAG — Chat, Agent, Knowledge Retrieval"])
app.include_router(platform_routes.router, prefix="/api/platform", tags=["Platform Intelligence — Lineage/Quality/Streaming/Compliance"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Healthcare Data Intelligence Platform",
        "status": "healthy",
        "version": "3.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    if DEMO_MODE:
        from pathlib import Path
        demo_db = Path(__file__).parent.parent / "demo" / "healthcare_demo.db"
        if not demo_db.exists():
            raise HTTPException(status_code=503, detail="Demo database not found — run 'python demo/seed_database.py'")
        return {"status": "healthy", "mode": "demo", "backend": "sqlite"}

    try:
        from config.snowflake_config import get_snowflake_connection
        conn = get_snowflake_connection()
        conn.close()
        return {"status": "healthy", "mode": "production", "snowflake": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Snowflake unreachable: {str(e)}")


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus scrape endpoint."""
    return await metrics_endpoint()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

"""
Monitoring & Logging Middleware
- Structured JSON logging (production-ready, parseable by ELK/CloudWatch)
- Prometheus metrics: request count, latency histogram, error rate
- Request ID tracing for cross-service debugging
"""

import time
import json
import logging
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# ─── Structured JSON Logging ───────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)


logger = logging.getLogger("HealthcareAPI.monitoring")

# ─── Prometheus Metrics ─────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency",
    ["method", "endpoint"],
)
ERROR_COUNT = Counter(
    "http_errors_total", "Total HTTP 5xx errors",
    ["method", "endpoint"],
)
AI_QUERY_COUNT = Counter(
    "ai_queries_total", "Total AI/NL2SQL queries processed",
    ["status"],  # success | rejected | failed
)
SNOWFLAKE_QUERY_LATENCY = Histogram(
    "snowflake_query_duration_seconds", "Snowflake query latency",
)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Attaches request-id, logs each request, and records Prometheus metrics."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        endpoint = request.url.path

        REQUEST_COUNT.labels(
            method=request.method, endpoint=endpoint, status_code=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)

        if response.status_code >= 500:
            ERROR_COUNT.labels(method=request.method, endpoint=endpoint).inc()

        logger.info(
            f"{request.method} {endpoint} → {response.status_code}",
            extra={"request_id": request_id, "duration_ms": round(duration * 1000, 2)},
        )

        response.headers["X-Request-ID"] = request_id
        return response


async def metrics_endpoint():
    """Exposes /metrics for Prometheus scraping."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

"""
Rate Limiting
Application-level rate limits, independent of the Ingress-level nginx
annotation (infra/k8s/frontend/deployment.yaml) which only protects at the
edge for K8s deployments — this also covers local/docker-compose runs where
no Ingress exists, and lets different endpoints have different limits
(login needs much stricter limits than a dashboard read).

Uses slowapi (a FastAPI-native wrapper around the battle-tested `limits`
library), keyed by client IP by default and by username for authenticated
routes where brute-force/abuse-per-account matters more than per-IP.
"""

import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("RateLimiting")


def _rate_limit_key(request: Request) -> str:
    """
    Keys by authenticated username when available (so a single abusive
    account is throttled regardless of IP rotation), falling back to
    client IP for unauthenticated routes like /api/auth/login.
    """
    username = getattr(request.state, "authenticated_username", None)
    return username or get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key, default_limits=["200/minute"])


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom 429 response — logs the abuse attempt (useful signal for security review)."""
    logger.warning(f"Rate limit exceeded: {_rate_limit_key(request)} on {request.url.path}")
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please slow down and try again shortly.",
            "retry_after_seconds": 60,
        },
    )


# ─── Per-route limit presets (applied via @limiter.limit(...) decorator) ───────
# Login gets the strictest limit — brute-force protection was the concrete
# gap identified in the audit (no protection existed before this module).
LOGIN_RATE_LIMIT = "5/minute"          # 5 attempts/min per IP — enough for a typo, not a brute force
AI_QUERY_RATE_LIMIT = "20/minute"      # LLM calls are the most expensive resource — throttle harder
STANDARD_READ_RATE_LIMIT = "100/minute"

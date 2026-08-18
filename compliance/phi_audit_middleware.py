"""
PHI Access Audit Middleware
Extends the AI-query-specific audit trail (AUDIT.AI_QUERY_LOG) to log EVERY
request against a route tagged as PHI-adjacent — required by HIPAA's audit
control standard (45 CFR §164.312(b)), which covers all PHI access, not just
AI-assisted queries.

Usage: tag a router with `phi_route=True` and mount this middleware once in
main.py. Routes not tagged are logged at INFO (normal request logging via
monitoring.py) but not written to the PHI audit table — avoids treating
every health-check ping as a compliance event.
"""

import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("PHIAuditMiddleware")

# Routes considered PHI-adjacent for audit purposes — in this project's
# current dataset (de-identified CMS PUF, see HIPAA_COMPLIANCE.md) nothing
# is *actually* PHI, but every route that touches per-prescriber or
# per-patient-adjacent granularity is audited as if it were, so the audit
# path is already correct the day real claims data replaces the demo dataset.
PHI_ADJACENT_PATH_PREFIXES = (
    "/api/prescribers/",
    "/api/ai/",
    "/api/rag/",
)


def _is_phi_adjacent(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in PHI_ADJACENT_PATH_PREFIXES)


class PHIAuditMiddleware(BaseHTTPMiddleware):
    """Logs (user, path, method, status, latency, client IP) for every PHI-adjacent request."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_phi_route = _is_phi_adjacent(path)
        start = time.time()

        response = await call_next(request)

        if is_phi_route:
            duration_ms = round((time.time() - start) * 1000, 2)
            # `request.state.user` is set by the JWT dependency after auth resolves;
            # unauthenticated requests (401s) still get logged with user=None.
            username = getattr(request.state, "authenticated_username", None)

            self._write_audit_record(
                username=username,
                path=path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_ip=request.client.host if request.client else "unknown",
            )

        return response

    def _write_audit_record(self, username, path, method, status_code, duration_ms, client_ip):
        """
        Writes to AUDIT.PHI_ACCESS_LOG (see data_retention_policy.sql for the
        table DDL + retention rule). Failure to write audit logs must never
        crash the request — but IS itself logged loudly, since a silently
        broken audit trail is a compliance gap.
        """
        try:
            from config.snowflake_config import run_query
            run_query(
                """
                INSERT INTO AUDIT.PHI_ACCESS_LOG
                    (username, path, method, status_code, duration_ms, client_ip, accessed_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
                """,
                (username, path, method, status_code, duration_ms, client_ip),
            )
        except Exception as e:
            logger.error(
                f"PHI AUDIT WRITE FAILED — compliance gap: user={username} path={path} "
                f"status={status_code}. Error: {e}"
            )

"""
JWT Token Blacklist
Addresses a gap flagged in the security audit: a JWT stays valid until its
natural expiry even after "logout" — there was no revocation mechanism.

In-memory by default (fine for a single API replica / local demo); the
K8s deployment runs multiple replicas (infra/k8s/api/deployment.yaml, HPA
2-10 pods), so production MUST back this with Redis (or any shared store)
instead — the interface below is written so swapping the backend is a
one-function change (see `_store` abstraction).
"""

import time
import logging
import os

logger = logging.getLogger("TokenBlacklist")

# ─── Backend selection ─────────────────────────────────────────────────────
# REDIS_URL set → use Redis (required for multi-replica correctness — an
# in-memory blacklist on pod A doesn't protect requests routed to pod B).
# Not set → in-memory fallback (single-process local/demo use only).
_REDIS_URL = os.environ.get("REDIS_URL")
_redis_client = None

if _REDIS_URL:
    try:
        import redis
        _redis_client = redis.from_url(_REDIS_URL, decode_responses=True)
        logger.info("Token blacklist backed by Redis (multi-replica safe)")
    except ImportError:
        logger.warning("REDIS_URL set but redis package not installed — falling back to in-memory (NOT multi-replica safe)")
else:
    logger.warning("No REDIS_URL configured — token blacklist is in-memory only. "
                    "Fine for local/demo; production with >1 API replica MUST set REDIS_URL.")

_in_memory_blacklist: dict[str, float] = {}  # jti -> expiry timestamp


def blacklist_token(jti: str, expires_at: float):
    """
    Marks a token's unique id (jti) as revoked until its own natural expiry
    (no point keeping it blacklisted past the point it would expire anyway).
    """
    if _redis_client:
        ttl_seconds = max(1, int(expires_at - time.time()))
        _redis_client.setex(f"blacklist:{jti}", ttl_seconds, "1")
    else:
        _in_memory_blacklist[jti] = expires_at
    logger.info(f"Token revoked: jti={jti[:8]}...")


def is_token_blacklisted(jti: str) -> bool:
    if _redis_client:
        return _redis_client.exists(f"blacklist:{jti}") == 1

    expiry = _in_memory_blacklist.get(jti)
    if expiry is None:
        return False
    if expiry < time.time():
        # Naturally expired — clean up and treat as not-blacklisted
        # (the token would fail JWT expiry validation anyway).
        _in_memory_blacklist.pop(jti, None)
        return False
    return True

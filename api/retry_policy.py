"""
Retry / Exponential Backoff
Wraps external service calls (OpenAI, Snowflake) that were previously
unprotected — a single transient network blip or a momentary Snowflake
warehouse-resume delay would fail the entire user request instead of
quietly retrying. Uses `tenacity`, the standard Python retry library.

Policy: 3 attempts, exponential backoff starting at 1s (1s → 2s → 4s),
capped at 10s between attempts — matches the "3 attempts, exponential
backoff" requirement flagged as missing in the engineering audit.
"""

import logging
from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception_type,
    before_sleep_log, RetryError,
)

logger = logging.getLogger("RetryPolicy")

# ─── Snowflake ──────────────────────────────────────────────────────────────
# Retries on connection/network errors, NOT on SQL syntax errors (those are
# deterministic — retrying a broken query 3 times just wastes 3x the time
# before failing the same way). snowflake.connector.errors is imported
# lazily inside the decorator factory so this module has no hard dependency
# on the snowflake package (keeps it importable in contexts that don't need it).
def snowflake_retry():
    try:
        from snowflake.connector.errors import OperationalError, DatabaseError
        retryable_exceptions = (OperationalError, DatabaseError, ConnectionError, TimeoutError)
    except ImportError:
        retryable_exceptions = (ConnectionError, TimeoutError)

    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(retryable_exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,  # after 3 failed attempts, raise the real error (not a generic RetryError)
    )


# ─── OpenAI ─────────────────────────────────────────────────────────────────
# Retries on rate limits and transient server/connection errors — NOT on
# authentication errors or bad-request errors (retrying an invalid API key
# 3 times is pointless and just adds latency to a failure that needs a
# human to fix, not a retry).
def openai_retry():
    try:
        from openai import RateLimitError, APIConnectionError, APITimeoutError, InternalServerError
        retryable_exceptions = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)
    except ImportError:
        retryable_exceptions = (ConnectionError, TimeoutError)

    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(retryable_exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

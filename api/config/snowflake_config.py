"""
Snowflake Connection Management
Fixes two gaps flagged in the engineering audit:
  1. No connection pooling — every run_query() call opened a brand-new
     TCP+auth handshake to Snowflake, which is slow (100s of ms of pure
     connection overhead per request) and exhausts Snowflake's per-user
     connection limit under concurrent load.
  2. No retry/backoff — a single transient network blip failed the whole
     request instead of retrying.
"""

import os
import logging
import threading
import queue
import time
import snowflake.connector
from snowflake.connector import DictCursor
from contextlib import contextmanager

from retry_policy import snowflake_retry

logger = logging.getLogger("SnowflakeConfig")

POOL_MIN_SIZE = int(os.environ.get("SNOWFLAKE_POOL_MIN", "2"))
POOL_MAX_SIZE = int(os.environ.get("SNOWFLAKE_POOL_MAX", "10"))
CONNECTION_MAX_AGE_SECONDS = 3600  # recycle connections hourly (avoids stale/expired sessions)


def _create_connection():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "HEALTHCARE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "HEALTHCARE_DW"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "GOLD_SCHEMA"),
        role=os.environ.get("SNOWFLAKE_ROLE", "HEALTHCARE_READER"),
        client_session_keep_alive=True,
    )


class SnowflakeConnectionPool:
    """
    A minimal thread-safe connection pool. Each FastAPI worker process gets
    its own pool instance (module-level singleton per process — uvicorn
    --workers 2 in Dockerfile.api means 2 independent pools, which is
    correct: connections aren't fork-safe to share across processes).
    """

    def __init__(self, min_size: int = POOL_MIN_SIZE, max_size: int = POOL_MAX_SIZE):
        self._max_size = max_size
        self._pool: queue.Queue = queue.Queue(maxsize=max_size)
        self._created_count = 0
        self._lock = threading.Lock()

        for _ in range(min_size):
            self._pool.put((_create_connection(), time.time()))
            self._created_count += 1

        logger.info(f"Snowflake connection pool initialized: {min_size} connections (max {max_size})")

    def _get_or_create(self):
        try:
            conn, created_at = self._pool.get_nowait()
            if time.time() - created_at > CONNECTION_MAX_AGE_SECONDS or conn.is_closed():
                logger.info("Recycling stale/closed pooled connection")
                conn = _create_connection()
                created_at = time.time()
            return conn, created_at
        except queue.Empty:
            with self._lock:
                if self._created_count < self._max_size:
                    self._created_count += 1
                    logger.info(f"Pool exhausted — opening new connection ({self._created_count}/{self._max_size})")
                    return _create_connection(), time.time()
            # Pool at max capacity — block until a connection is returned
            # rather than opening unbounded connections (protects Snowflake's
            # per-user connection limit under load spikes).
            logger.warning("Connection pool at max capacity — waiting for a free connection")
            conn, created_at = self._pool.get(timeout=30)
            return conn, created_at

    @contextmanager
    def acquire(self):
        conn, created_at = self._get_or_create()
        try:
            yield conn
        finally:
            try:
                self._pool.put_nowait((conn, created_at))
            except queue.Full:
                conn.close()  # pool already full (shouldn't normally happen) — just close it


_pool: SnowflakeConnectionPool | None = None
_pool_lock = threading.Lock()


def get_pool() -> SnowflakeConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:  # double-checked locking
                _pool = SnowflakeConnectionPool()
    return _pool


def get_snowflake_connection():
    """
    Kept for backward compatibility with call sites that want a raw,
    non-pooled connection (e.g. the one-off startup health check in
    main.py's lifespan). New code should prefer run_query()/snowflake_cursor()
    below, which use the pool.
    """
    return _create_connection()


@contextmanager
def snowflake_cursor():
    """Pooled context manager yielding a dict-cursor. Returns the connection to the pool on exit (does not close it)."""
    pool = get_pool()
    with pool.acquire() as conn:
        cursor = conn.cursor(DictCursor)
        try:
            yield cursor
        finally:
            cursor.close()


@snowflake_retry()
def run_query(sql: str, params: tuple = None) -> list[dict]:
    """
    Execute a query (pooled connection, 3x retry with exponential backoff on
    transient errors) — or, in demo mode, transparently against the local
    SQLite demo database instead. See config/demo_mode.py.
    """
    from config.demo_mode import DEMO_MODE, run_query_sqlite
    if DEMO_MODE:
        return run_query_sqlite(sql, params)

    with snowflake_cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchall()

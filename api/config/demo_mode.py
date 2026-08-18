"""
Demo Mode Switch
Single source of truth for whether the API is running against real cloud
services (Snowflake + OpenAI) or the local demo stack (SQLite + mock LLM).
Controlled by the DEMO_MODE environment variable — set in
docker/docker-compose.demo.yml, absent in docker/docker-compose.yml
(production/full stack).

config.snowflake_config.run_query() checks DEMO_MODE at the top of every
call and delegates to run_query_sqlite() below when active — this means
every route in api/routes/ needed ZERO changes to support demo mode; they
all already call run_query() through the one choke point.
"""

import os
import logging

logger = logging.getLogger("DemoMode")

DEMO_MODE = os.environ.get("DEMO_MODE", "false").strip().lower() == "true"

if DEMO_MODE:
    logger.warning(
        "🎭 DEMO MODE ACTIVE — using SQLite (demo/healthcare_demo.db) instead of "
        "Snowflake, and pattern-matched mock responses instead of OpenAI. "
        "Set DEMO_MODE=false (or unset it) for the real cloud-connected stack."
    )


def run_query_sqlite(sql: str, params: tuple = None) -> list[dict]:
    """
    Translates the small set of Snowflake-flavored SQL this codebase
    generates (uppercase schema-qualified table names, %s placeholders) into
    flat SQLite table names + ? placeholders, and runs it against
    demo/healthcare_demo.db. Handles exactly the SELECT/GROUP BY/ORDER BY/
    LIMIT surface this project actually issues — not a general SQL dialect
    translator, which would be over-engineering for a demo mode.
    """
    import re
    import sqlite3
    from pathlib import Path

    demo_db = Path(__file__).parent.parent.parent / "demo" / "healthcare_demo.db"
    if not demo_db.exists():
        raise FileNotFoundError(
            f"Demo database not found at {demo_db}. Run: python demo/seed_database.py"
        )

    conn = sqlite3.connect(demo_db)
    conn.row_factory = sqlite3.Row

    # Strip schema prefixes and convert %s to ?
    translated_sql = re.sub(r"(?i)\bGOLD_SCHEMA\.", "", sql)
    translated_sql = re.sub(r"(?i)\bAUTH_SCHEMA\.", "", translated_sql)
    translated_sql = re.sub(r"(?i)\bAUDIT\.", "", translated_sql)
    translated_sql = translated_sql.replace("%s", "?")

    # SQLite does not support standard STDDEV or HAVING without GROUP BY in some CTEs, so handle gracefully
    try:
        cursor = conn.execute(translated_sql, params or ())
        results = []
        for row in cursor.fetchall():
            # Return dict with uppercase keys to ensure 100% compatibility with Snowflake response handlers
            d = dict(row)
            upper_d = {k.upper(): v for k, v in d.items()}
            # Also keep lowercase keys for flexible access
            upper_d.update({k.lower(): v for k, v in d.items()})
            results.append(upper_d)
        return results
    except Exception as e:
        logger.error(f"Demo SQLite query error: {e} | SQL: {translated_sql}")
        return []
    finally:
        conn.close()

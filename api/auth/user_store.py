"""
User Store
For this project, users live in a Snowflake table (AUTH_SCHEMA.USERS).
Falls back to an in-memory seed set if the table hasn't been provisioned yet
(useful for local dev / demoing without full Snowflake setup).
"""

from config.snowflake_config import run_query
from auth.jwt_handler import hash_password
import logging

logger = logging.getLogger("UserStore")

# Seed users for local/demo mode — passwords are bcrypt-hashed at import time
_DEMO_USERS = {
    "admin": {
        "username": "admin",
        "email": "admin@healthcare.com",
        "full_name": "Platform Admin",
        "role": "admin",
        "hashed_password": hash_password("Admin@123"),
    },
    "analyst": {
        "username": "analyst",
        "email": "analyst@healthcare.com",
        "full_name": "Data Analyst",
        "role": "analyst",
        "hashed_password": hash_password("Analyst@123"),
    },
    "viewer": {
        "username": "viewer",
        "email": "viewer@healthcare.com",
        "full_name": "Dashboard Viewer",
        "role": "viewer",
        "hashed_password": hash_password("Viewer@123"),
    },
}


def get_user_by_username(username: str) -> dict | None:
    """Look up a user by username. Tries Snowflake first, falls back to demo set."""
    try:
        rows = run_query(
            "SELECT username, email, full_name, role, hashed_password "
            "FROM AUTH_SCHEMA.USERS WHERE username = %s AND is_active = TRUE",
            (username,),
        )
        if rows:
            return rows[0]
    except Exception as e:
        logger.warning(f"Snowflake user lookup failed, using demo users: {e}")

    return _DEMO_USERS.get(username)


def create_user(username: str, email: str, full_name: str, password: str, role: str = "viewer") -> dict:
    """Insert a new user into AUTH_SCHEMA.USERS (admin-only operation)."""
    hashed = hash_password(password)
    run_query(
        """
        INSERT INTO AUTH_SCHEMA.USERS (username, email, full_name, role, hashed_password, is_active, created_at)
        VALUES (%s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP())
        """,
        (username, email, full_name, role, hashed),
    )
    return {"username": username, "email": email, "full_name": full_name, "role": role}

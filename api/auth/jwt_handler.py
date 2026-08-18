"""
JWT Authentication Core
Handles password hashing, token creation/verification, and current-user resolution.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# ─── Config ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ─── Models ───────────────────────────────────────────────────────────────────
class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class UserOut(BaseModel):
    username: str
    email: str
    role: str
    full_name: str


# ─── Password Utilities ────────────────────────────────────────────────────────
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ─── Token Utilities ────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # jti (JWT ID) — unique per-token identifier, required for revocation:
    # blacklisting works by jti, not by the token string itself (avoids
    # storing/comparing full tokens, which is both wasteful and a minor
    # info-leak risk in logs/storage).
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "access", "jti": jti})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── Dependency: Get Current User ──────────────────────────────────────────────
async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> TokenData:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Revocation check — closes the "logout doesn't actually invalidate the
    # token" gap flagged in the audit. See auth/token_blacklist.py.
    from auth.token_blacklist import is_token_blacklisted
    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Token has been revoked (logged out)")

    username: str = payload.get("sub")
    role: str = payload.get("role")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Exposes the authenticated username to PHIAuditMiddleware (compliance/
    # phi_audit_middleware.py), which runs after route dependencies resolve
    # and reads this off request.state to attribute PHI-adjacent access logs
    # to a specific user rather than logging them as anonymous.
    request.state.authenticated_username = username
    request.state.current_jti = jti
    request.state.current_token_exp = payload.get("exp")

    return TokenData(username=username, role=role)


# ─── Role-Based Access Control ─────────────────────────────────────────────────
class RoleChecker:
    """
    Usage:
        @router.get("/admin-only", dependencies=[Depends(RoleChecker(["admin"]))])
    """
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: TokenData = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted. Required: {self.allowed_roles}",
            )
        return current_user


# ─── Role Definitions (mirrors DB roles table) ─────────────────────────────────
class Roles:
    ADMIN = "admin"           # full access — manage users, all data, pipeline triggers
    ANALYST = "analyst"       # read all Gold data + AI assistant
    VIEWER = "viewer"         # read-only dashboards, no AI/export

require_admin = RoleChecker([Roles.ADMIN])
require_analyst_or_admin = RoleChecker([Roles.ADMIN, Roles.ANALYST])
require_any_role = RoleChecker([Roles.ADMIN, Roles.ANALYST, Roles.VIEWER])

"""Authentication routes: login, token refresh, current-user info, user creation."""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import logging

from auth.jwt_handler import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, get_current_user, require_admin, TokenData, UserOut,
)
from auth.user_store import get_user_by_username, create_user
from auth.token_blacklist import blacklist_token, is_token_blacklisted
from rate_limiting import limiter, LOGIN_RATE_LIMIT

logger = logging.getLogger("AuthRoutes")
router = APIRouter()


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class CreateUserRequest(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: str = "viewer"


@router.post("/login", response_model=LoginResponse)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2-compatible login. Send as form-data: username, password.
    Demo accounts: admin/Admin@123, analyst/Analyst@123, viewer/Viewer@123
    Rate-limited to 5 attempts/minute per IP — brute-force protection that
    was previously entirely absent (flagged in the security audit).
    """
    user = get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token_payload = {"sub": user["username"], "role": user["role"]}
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    logger.info(f"User '{user['username']}' logged in with role '{user['role']}'")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
    }


@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    """Exchange a valid refresh token for a new access token."""
    payload = decode_token(request.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type — refresh token required")

    new_access_token = create_access_token({"sub": payload["sub"], "role": payload["role"]})
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(request: Request, current_user: TokenData = Depends(get_current_user)):
    """
    Revokes the current access token immediately (previously: tokens stayed
    valid until natural expiry regardless of "logout" — flagged in the audit).
    The frontend should still discard the token from localStorage on its
    side (context/AuthContext.tsx::logout already does this) — this endpoint
    additionally ensures the token can't be replayed server-side even if
    captured/leaked before the client discarded it.
    """
    jti = getattr(request.state, "current_jti", None)
    exp = getattr(request.state, "current_token_exp", None)

    if jti and exp:
        blacklist_token(jti, exp)
        logger.info(f"User '{current_user.username}' logged out — token {jti[:8]}... revoked")

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    user = get_user_by_username(current_user.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "full_name": user["full_name"],
    }


@router.post("/users", dependencies=[Depends(require_admin)])
async def create_new_user(request: CreateUserRequest):
    """Admin-only: create a new platform user with a specific role."""
    if request.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")
    try:
        user = create_user(
            request.username, request.email, request.full_name,
            request.password, request.role,
        )
        return {"message": "User created", "user": user}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

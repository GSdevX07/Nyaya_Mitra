"""
auth/routes.py — Authentication API endpoints for Nyaya Mitra.

Endpoints:
  POST /auth/login           — credential login → access + refresh tokens
  POST /auth/refresh         — exchange refresh → new access token
  POST /auth/logout          — revoke current token pair
  GET  /auth/me              — current user profile
  POST /auth/change-password — update password (requires current)
  POST /auth/demo-token      — demo quick-login (DEMO_MODE only)
  GET  /auth/demo-users      — list available demo accounts (DEMO_MODE only)
"""
from __future__ import annotations
import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from app.auth.config import DEMO_MODE, JWT_ACCESS_TTL_MINUTES
from app.auth.brute_force import check_lockout, clear_attempts, record_failed_attempt
from app.auth.dependencies import get_current_user
from app.auth.password import hash_password, validate_password_strength, verify_password
from app.auth.roles import Role
from app.auth.session_store import revoke_token
from app.auth.tokens import create_access_token, create_refresh_token, decode_refresh_token
from app.auth.user_store import (
    AuthUser,
    get_all_demo_users,
    get_password_hash_for_email,
    get_user_by_email,
    get_user_by_id,
    update_last_login,
)

auth_router = APIRouter(tags=["Authentication"])
_bearer = HTTPBearer(auto_error=False)


# ── Request / Response models ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user_id: str
    role: str
    full_name: str
    org_id: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class DemoTokenRequest(BaseModel):
    role: str  # One of the Role enum values


# ── Helpers ───────────────────────────────────────────────────────────────────

def _issue_tokens(user: AuthUser) -> TokenResponse:
    extra = {"district": user.district}
    if getattr(user, "linked_case_id", None):
        extra["linked_case_id"] = user.linked_case_id
    if getattr(user, "full_name", None):
        extra["full_name"] = user.full_name
    access = create_access_token(
        subject=user.id,
        role=user.role.value,
        org_id=user.org_id,
        facility_ids=user.facility_ids,
        extra_claims=extra,
    )
    refresh = create_refresh_token(subject=user.id)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in_seconds=JWT_ACCESS_TTL_MINUTES * 60,
        user_id=user.id,
        role=user.role.value,
        full_name=user.full_name,
        org_id=user.org_id,
    )


def _write_audit_login(user_id: str, ip: str, success: bool) -> None:
    try:
        from app.repositories.audit_repository import append_audit_event
        append_audit_event({
            "entity_type": "user",
            "entity_id": user_id,
            "action": "LOGIN" if success else "LOGIN_FAILED",
            "actor_id": user_id,
            "actor_role": "AUTH",
            "details": {"ip": ip, "success": success},
        })
    except Exception:
        pass


# ── Routes ────────────────────────────────────────────────────────────────────

@auth_router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    """
    Authenticate with email + password.
    Returns a short-lived access token and a longer-lived refresh token.
    Applies brute-force protection: progressive delay and lockout.
    """
    email = body.email.lower().strip()
    ip = request.client.host if request.client else "unknown"

    await check_lockout(email)

    stored_hash = get_password_hash_for_email(email)
    user = get_user_by_email(email)

    if not stored_hash or not user or not verify_password(body.password, stored_hash):
        record_failed_attempt(email)
        _write_audit_login(user.id if user else email, ip, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated. Contact your administrator.",
        )

    clear_attempts(email)
    update_last_login(user.id)
    _write_audit_login(user.id, ip, True)

    return _issue_tokens(user)


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest):
    """Exchange a valid refresh token for a new access token."""
    payload = decode_refresh_token(body.refresh_token)
    user_id = payload.get("sub")
    user = get_user_by_id(user_id) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cannot refresh token.")

    # Revoke old refresh token
    jti = payload.get("jti", "")
    if jti:
        exp_ts = payload.get("exp")
        exp_dt = datetime.datetime.fromtimestamp(exp_ts, tz=datetime.timezone.utc) if exp_ts else (
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        )
        revoke_token(jti, exp_dt, user_id=user.id)

    return _issue_tokens(user)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    current_user: AuthUser = Depends(get_current_user),
):
    """Revoke the current access token. Client should also discard the refresh token."""
    if credentials:
        from app.auth.tokens import decode_token
        try:
            payload = decode_token(credentials.credentials)
            jti = payload.get("jti", "")
            exp = payload.get("exp")
            if jti and exp:
                exp_dt = datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc)
                revoke_token(jti, exp_dt, user_id=current_user.id)
        except Exception:
            pass

    try:
        from app.repositories.audit_repository import append_audit_event
        append_audit_event({
            "entity_type": "user",
            "entity_id": current_user.id,
            "action": "TOKEN_REVOCATION",
            "actor_id": current_user.id,
            "actor_role": current_user.role.value,
            "details": {"reason": "user_logout"},
        })
    except Exception:
        pass


@auth_router.get("/me")
async def get_me(current_user: AuthUser = Depends(get_current_user)):
    """Return the current user's profile and role from the database."""
    return {
        "id": current_user.id,
        "email": getattr(current_user, "email", ""),
        "role": current_user.role.value,
        "full_name": current_user.full_name,
        "org_id": current_user.org_id,
        "district": current_user.district,
        "facility_ids": current_user.facility_ids,
        "linked_case_id": current_user.linked_case_id,
        "phone": getattr(current_user, "phone", "") or "+91 11 2338 1234",
        "relationship_to_accused": getattr(current_user, "relationship_to_accused", None),
        "bar_registration_no": getattr(current_user, "bar_registration_no", None),
    }


@auth_router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Change password — requires current password for verification."""
    stored_hash = get_password_hash_for_email(getattr(current_user, "email", ""))
    if not stored_hash or not verify_password(body.current_password, stored_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect.")

    errors = validate_password_strength(body.new_password)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

    new_hash = hash_password(body.new_password)
    # Persist (best-effort)
    try:
        from app.supabase_adapter import get_supabase_client
        client = get_supabase_client()
        if client:
            client.table("organization_users").update({"password_hash": new_hash}).eq("id", current_user.id).execute()
    except Exception:
        pass
    try:
        from app.database import get_db_connection
        conn = get_db_connection()
        conn.execute("UPDATE organization_users SET password_hash=? WHERE id=?", (new_hash, current_user.id))
        conn.commit()
        conn.close()
    except Exception:
        pass


@auth_router.post("/demo-token", response_model=TokenResponse)
async def demo_token(body: DemoTokenRequest):
    """
    Issue a short-lived JWT for the requested demo role.

    BLOCKED in production (DEMO_MODE=false). Only for hackathon/demo environments.
    """
    if not DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo tokens are not available in production mode.",
        )

    try:
        role = Role(body.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown role: {body.role}")

    # Find the demo user for this role
    from app.auth.user_store import _DEMO_USER_DEFINITIONS, _build_demo_users, _DEMO_USERS, _row_to_user
    _build_demo_users()
    demo_entry = next(
        (d for d in _DEMO_USER_DEFINITIONS if d["role"] == role.value), None
    )
    if not demo_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No demo user for role {role.value}")

    user_data = _DEMO_USERS.get(demo_entry["email"])
    if not user_data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Demo user not initialized.")

    user = _row_to_user(user_data)
    return _issue_tokens(user)


@auth_router.get("/demo-users")
async def list_demo_users():
    """
    List available demo accounts with their roles and credentials.
    BLOCKED in production (DEMO_MODE=false).
    """
    if not DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo user listing is not available in production mode.",
        )
    return {"demo_users": get_all_demo_users(), "demo_password": "Demo@12345"}

"""
auth/dependencies.py — FastAPI dependency factories for auth enforcement.

Usage in routes:
    @app.get("/cases", dependencies=[Depends(require_role(Role.DLSA_OFFICER, Role.PLATFORM_ADMIN))])
    def get_cases(current_user: AuthUser = Depends(get_current_user)):
        ...
"""
from __future__ import annotations
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.roles import Role
from app.auth.tokens import decode_token
from app.auth.session_store import is_revoked
from app.auth.user_store import AuthUser, get_user_by_id

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthUser:
    """
    FastAPI dependency that extracts and validates the Bearer JWT,
    checks revocation, and loads the full user from the store.

    Raises 401 on any failure.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)

    jti = payload.get("jti", "")
    if jti and is_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

    user = get_user_by_id(user_id)
    if user is None:
        from app.auth.config import DEMO_MODE, APP_ENV
        token_role = payload.get("role")
        # In production, or for PLATFORM_ADMIN, or for deleted/revoked users,
        # missing user from authoritative identity store is strictly rejected (401).
        if (
            APP_ENV == "production"
            or not DEMO_MODE
            or (token_role and token_role == Role.PLATFORM_ADMIN.value)
            or user_id.startswith("deleted_")
            or user_id.startswith("revoked_")
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account no longer exists in authoritative identity store.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if token_role:
            try:
                user = AuthUser(
                    id=user_id,
                    email=f"{user_id}@demo.nyayamitra.in",
                    role=Role(token_role),
                    org_id=payload.get("org_id", "org_dlsa_central"),
                    facility_ids=payload.get("facility_ids", []),
                    district=payload.get("district", "Central Delhi"),
                    full_name=f"Officer {user_id}",
                    is_active=True,
                )
            except Exception:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid role in token.")
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is inactive.")

    token_linked_case = payload.get("linked_case_id")
    if token_linked_case:
        user.linked_case_id = token_linked_case

    token_full_name = payload.get("full_name")
    if token_full_name:
        user.full_name = token_full_name

    token_facilities = payload.get("facility_ids")
    if token_facilities and not user.facility_ids:
        user.facility_ids = token_facilities

    token_station_id = payload.get("police_station_id")
    if token_station_id:
        user.police_station_id = token_station_id

    token_station = payload.get("police_station")
    if token_station:
        user.police_station = token_station

    token_jurisdictions = payload.get("jurisdiction_ids")
    if token_jurisdictions and not user.jurisdiction_ids:
        user.jurisdiction_ids = token_jurisdictions

    token_state_id = payload.get("state_id")
    if token_state_id:
        user.state_id = token_state_id

    token_state = payload.get("state")
    if token_state:
        user.state = token_state

    token_scope = payload.get("scope_type")
    if token_scope:
        user.scope_type = token_scope

    token_dist_ids = payload.get("authorized_district_ids")
    if token_dist_ids and not user.authorized_district_ids:
        user.authorized_district_ids = token_dist_ids

    return user


def require_role(*roles: Role) -> Callable:
    """
    Factory returning a FastAPI dependency that checks `current_user.role in roles`.

    Usage:
        @app.post("/approve", dependencies=[Depends(require_role(Role.SUPERVISING_LEGAL_OFFICER))])
    """
    role_set = set(roles)

    async def _check(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if current_user.role not in role_set:
            try:
                from app.repositories.audit_repository import audit_authorization_denied
                audit_authorization_denied(
                    user_id=current_user.id,
                    user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
                    required_roles=[r.value for r in role_set],
                    attempted_action="ROLE_GUARD_CHECK",
                )
            except Exception:
                pass

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): "
                    f"{', '.join(r.value for r in role_set)}. "
                    f"Your role: {current_user.role.value}."
                ),
            )
        return current_user

    return _check


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthUser | None:
    """
    Like get_current_user but returns None instead of raising if no token.
    Use on routes that are public but show more data when authenticated.
    """
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        return get_user_by_id(user_id)
    except Exception:
        return None

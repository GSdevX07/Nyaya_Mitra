"""
auth/tokens.py — JWT access and refresh token creation and verification.

Access tokens are short-lived (default 60 min) and carry role, org_id,
facility_ids, and a jti (UUID) for per-token revocation.

Refresh tokens are longer-lived (default 7 days), minimal claims.
"""
from __future__ import annotations
import uuid
import datetime
from typing import Any

from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.auth.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_ACCESS_TTL_MINUTES,
    JWT_REFRESH_TTL_DAYS,
)

_REFRESH_TOKEN_TYPE = "refresh"
_ACCESS_TOKEN_TYPE = "access"


def create_access_token(
    subject: str,
    role: str,
    org_id: str,
    facility_ids: list[str] | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: User ID (primary key in organization_users).
        role: One of the Role enum values.
        org_id: Organization the user belongs to.
        facility_ids: List of facility IDs the user can access.
        extra_claims: Any additional claims to embed (e.g. district).

    Returns:
        Signed JWT string.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "org_id": org_id,
        "facility_ids": facility_ids or [],
        "type": _ACCESS_TOKEN_TYPE,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + datetime.timedelta(minutes=JWT_ACCESS_TTL_MINUTES),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """
    Create a signed JWT refresh token (minimal claims).

    Returns:
        Signed JWT string.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": _REFRESH_TOKEN_TYPE,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + datetime.timedelta(days=JWT_REFRESH_TTL_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = _ACCESS_TOKEN_TYPE) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Raises:
        HTTPException 401 if the token is invalid, expired, or wrong type.

    Returns:
        Decoded payload dict.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise credentials_exception

    if payload.get("type") != expected_type:
        raise credentials_exception

    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode a refresh token specifically."""
    return decode_token(token, expected_type=_REFRESH_TOKEN_TYPE)

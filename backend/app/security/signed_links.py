"""
security/signed_links.py — Cryptographic HMAC Time-Expiring Signed Document URLs.
==================================================================================
Prevents predictable document link harvesting and unauthorized direct file access.
Generates cryptographically signed, short-lived tokens for secure file downloads.
"""

from __future__ import annotations
import base64
import hashlib
import hmac
import json
import time
import secrets
from typing import Optional, Tuple
from pydantic import BaseModel
from app.auth.config import JWT_SECRET


class SignedTokenPayload(BaseModel):
    doc_id: str
    user_id: str
    user_role: str = "AUTHENTICATED"
    exp: int
    nonce: str


def generate_signed_document_token(
    doc_id: str,
    user_id: str,
    user_role: str = "AUTHENTICATED",
    ttl_seconds: int = 900,
    expires_in_seconds: Optional[int] = None,
) -> str:
    """
    Generate a cryptographic HMAC-SHA256 signed download token.
    Payload: doc_id | user_id | user_role | exp | nonce
    """
    duration = expires_in_seconds if expires_in_seconds is not None else ttl_seconds
    expires_at = int(time.time()) + duration
    nonce = secrets.token_hex(8)

    payload_dict = {
        "doc_id": doc_id,
        "user_id": user_id,
        "user_role": user_role,
        "exp": expires_at,
        "nonce": nonce,
    }
    payload_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
    signature = hmac.new(JWT_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8")
    return f"{encoded_payload}.{signature}"


def verify_signed_token(token: str) -> Optional[SignedTokenPayload]:
    """
    Validate signature and expiration of a signed document token.
    Returns parsed SignedTokenPayload if valid, otherwise None.
    """
    if not token or "." not in token:
        return None

    try:
        encoded_payload, signature = token.split(".", 1)
        payload_bytes = base64.urlsafe_b64decode(encoded_payload.encode("utf-8"))

        expected_signature = hmac.new(
            JWT_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return None

        payload_dict = json.loads(payload_bytes.decode("utf-8"))
        exp = payload_dict.get("exp", 0)

        # Check expiration
        if time.time() > exp:
            return None

        return SignedTokenPayload(
            doc_id=payload_dict["doc_id"],
            user_id=payload_dict["user_id"],
            user_role=payload_dict.get("user_role", "AUTHENTICATED"),
            exp=exp,
            nonce=payload_dict.get("nonce", ""),
        )
    except Exception:
        return None


def verify_signed_document_token(token: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Legacy helper returning tuple (is_valid, doc_id, user_id)."""
    payload = verify_signed_token(token)
    if payload:
        return True, payload.doc_id, payload.user_id
    return False, None, None


def generate_signed_document_url(
    doc_id: str,
    user_id: str,
    user_role: str = "AUTHENTICATED",
    base_url: str = "",
    ttl_seconds: int = 900,
    expires_in_seconds: Optional[int] = None,
) -> str:
    """Convenience helper returning relative or absolute signed download URL."""
    token = generate_signed_document_token(
        doc_id=doc_id,
        user_id=user_id,
        user_role=user_role,
        ttl_seconds=ttl_seconds,
        expires_in_seconds=expires_in_seconds,
    )
    prefix = base_url.rstrip("/") if base_url else ""
    return f"{prefix}/documents/download/signed/{token}"

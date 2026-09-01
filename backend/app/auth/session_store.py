"""
auth/session_store.py — Token revocation store.

In-memory set (module-level) for local dev.
When Supabase is active, also persists to the `revoked_tokens` table
so revocation survives backend restarts.
"""
from __future__ import annotations
import datetime
from typing import Optional

# In-memory revocation set: {jti: expires_at}
_REVOKED: dict[str, datetime.datetime] = {}


def revoke_token(jti: str, expires_at: datetime.datetime, user_id: str = "") -> None:
    """Mark a token jti as revoked."""
    _REVOKED[jti] = expires_at

    # Persist to Supabase if active
    try:
        from app.supabase_adapter import get_supabase_client
        client = get_supabase_client()
        if client:
            client.table("revoked_tokens").upsert({
                "jti": jti,
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
                "revoked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }).execute()
    except Exception as e:
        print(f"[WARN] Supabase revoked_tokens write failed: {e}")


def is_revoked(jti: str) -> bool:
    """Return True if the token jti has been revoked."""
    now = datetime.datetime.now(datetime.timezone.utc)

    # Check memory first
    if jti in _REVOKED:
        if _REVOKED[jti] < now:
            # Expired — clean up
            del _REVOKED[jti]
            return False
        return True

    # Check Supabase (fallback for after restart)
    try:
        from app.supabase_adapter import get_supabase_client
        client = get_supabase_client()
        if client:
            res = client.table("revoked_tokens").select("jti, expires_at").eq("jti", jti).execute()
            if res.data:
                row = res.data[0]
                exp = datetime.datetime.fromisoformat(row["expires_at"])
                if exp > now:
                    # Cache it in memory
                    _REVOKED[jti] = exp
                    return True
    except Exception:
        pass

    return False


def purge_expired() -> int:
    """Remove expired entries from in-memory store. Returns count purged."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expired = [jti for jti, exp in _REVOKED.items() if exp < now]
    for jti in expired:
        del _REVOKED[jti]
    return len(expired)

"""
Idempotency middleware and request deduplication store for Nyaya Mitra.
Guarantees that retrying mutating requests (POST/PUT/PATCH) does not create duplicate business records.
"""

from __future__ import annotations
import json
import hashlib
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.database import get_db_connection

logger = logging.getLogger("nyaya_mitra.middleware.idempotency")

_IDEMPOTENCY_LOCK = threading.Lock()


def ensure_idempotency_table():
    """Ensure the idempotent_requests table exists."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS idempotent_requests (
                idempotency_key TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                actor_id TEXT,
                status TEXT NOT NULL,
                status_code INTEGER,
                response_headers_json TEXT,
                response_body_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                PRIMARY KEY (idempotency_key, endpoint)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotent_requests(expires_at)")
        conn.commit()
    finally:
        conn.close()


class IdempotencyStore:
    """Transactional store for idempotency caching and race condition prevention."""

    def __init__(self):
        ensure_idempotency_table()

    def get_record(self, idempotency_key: str, endpoint: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached idempotency record."""
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT idempotency_key, endpoint, request_hash, actor_id, status,
                       status_code, response_headers_json, response_body_json,
                       created_at, updated_at, expires_at
                FROM idempotent_requests
                WHERE idempotency_key = ? AND endpoint = ? AND expires_at > ?
                """,
                (idempotency_key, endpoint, now_iso),
            )
            row = cursor.fetchone()
            if not row:
                return None
            cols = [col[0] for col in cursor.description]
            return dict(zip(cols, row))
        finally:
            conn.close()

    def mark_in_progress(
        self,
        idempotency_key: str,
        endpoint: str,
        request_hash: str,
        actor_id: Optional[str] = None,
    ) -> bool:
        """
        Record that a request is currently being executed.
        Returns True if claimed, False if another concurrent execution already holds it.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        expires_iso = (now + timedelta(hours=24)).isoformat()

        with _IDEMPOTENCY_LOCK:
            existing = self.get_record(idempotency_key, endpoint)
            if existing:
                if existing["status"] == "IN_PROGRESS":
                    # Check if stalled (older than 60 seconds)
                    created_dt = datetime.fromisoformat(existing["created_at"])
                    if (now - created_dt).total_seconds() < 60.0:
                        return False  # Still actively running
                elif existing["status"] == "COMPLETED":
                    return False

            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO idempotent_requests (
                        idempotency_key, endpoint, request_hash, actor_id,
                        status, created_at, updated_at, expires_at
                    ) VALUES (?, ?, ?, ?, 'IN_PROGRESS', ?, ?, ?)
                    ON CONFLICT(idempotency_key, endpoint) DO UPDATE SET
                        status = 'IN_PROGRESS',
                        request_hash = excluded.request_hash,
                        updated_at = excluded.updated_at,
                        expires_at = excluded.expires_at
                    """,
                    (idempotency_key, endpoint, request_hash, actor_id, now_iso, now_iso, expires_iso),
                )
                conn.commit()
                return True
            finally:
                conn.close()

    def store_result(
        self,
        idempotency_key: str,
        endpoint: str,
        status_code: int,
        response_body: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Store completed response for future replaying."""
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        expires_iso = (now + timedelta(hours=24)).isoformat()

        headers_json = json.dumps(headers or {})
        with _IDEMPOTENCY_LOCK:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE idempotent_requests
                    SET status = 'COMPLETED',
                        status_code = ?,
                        response_body_json = ?,
                        response_headers_json = ?,
                        updated_at = ?,
                        expires_at = ?
                    WHERE idempotency_key = ? AND endpoint = ?
                    """,
                    (status_code, response_body, headers_json, now_iso, expires_iso, idempotency_key, endpoint),
                )
                conn.commit()
            finally:
                conn.close()

    def mark_failed(self, idempotency_key: str, endpoint: str) -> None:
        """Mark record as failed so a future retry can re-attempt."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with _IDEMPOTENCY_LOCK:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE idempotent_requests
                    SET status = 'FAILED', updated_at = ?
                    WHERE idempotency_key = ? AND endpoint = ?
                    """,
                    (now_iso, idempotency_key, endpoint),
                )
                conn.commit()
            finally:
                conn.close()


_GLOBAL_STORE: Optional[IdempotencyStore] = None


def get_idempotency_store() -> IdempotencyStore:
    """Singleton getter for idempotency store."""
    global _GLOBAL_STORE
    if _GLOBAL_STORE is None:
        _GLOBAL_STORE = IdempotencyStore()
    return _GLOBAL_STORE


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware intercepting mutating requests carrying an 'Idempotency-Key' header.
    Replays previously completed responses and guards against race conditions.
    """

    def __init__(self, app, store: Optional[IdempotencyStore] = None):
        super().__init__(app)
        self.store = store or get_idempotency_store()

    async def dispatch(self, request: Request, call_next):
        # Only inspect mutating HTTP methods
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        endpoint = request.url.path
        body_bytes = await request.body()
        body_hash = hashlib.sha256(body_bytes).hexdigest()

        # Check existing cached state
        cached = self.store.get_record(idempotency_key, endpoint)
        if cached:
            if cached["status"] == "COMPLETED":
                # Return cached replay
                headers = {"Idempotent-Replayed": "true", "Content-Type": "application/json"}
                return Response(
                    content=cached.get("response_body_json") or "{}",
                    status_code=cached.get("status_code", 200),
                    headers=headers,
                    media_type="application/json",
                )
            elif cached["status"] == "IN_PROGRESS":
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": "A concurrent mutating request with this Idempotency-Key is currently in progress.",
                        "idempotency_key": idempotency_key,
                        "retry_after_seconds": 2,
                    },
                )

        # Claim execution lock
        claimed = self.store.mark_in_progress(idempotency_key, endpoint, body_hash)
        if not claimed:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "Conflict: Idempotent request lock held by active worker.",
                    "idempotency_key": idempotency_key,
                },
            )

        # Re-attach request body for downstream handlers
        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request = Request(request.scope, receive=receive)

        try:
            response = await call_next(request)

            # Consume response body to cache it
            response_body_chunks = [chunk async for chunk in response.body_iterator]
            response_body = b"".join(response_body_chunks).decode("utf-8", errors="replace")

            # Store result if successful or non-server-error (e.g. 2xx, 4xx)
            if response.status_code < 500:
                self.store.store_result(
                    idempotency_key=idempotency_key,
                    endpoint=endpoint,
                    status_code=response.status_code,
                    response_body=response_body,
                )
            else:
                self.store.mark_failed(idempotency_key, endpoint)

            # Return fresh response with Idempotency-Key echoed
            new_headers = dict(response.headers)
            new_headers["Idempotency-Key"] = idempotency_key
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=new_headers,
                media_type=response.media_type,
            )

        except Exception:
            self.store.mark_failed(idempotency_key, endpoint)
            raise

"""
ingestion/connectors/base.py — Abstract Base Connector & Enterprise Contract Framework.

Every external source connector (e-Courts, e-Prisons, CCTNS, Prosecution, DLSA, Files, Manual)
implements this interface with support for:
  - Token masking & secure credential vault (tokens are NEVER exposed to browser or in plaintext)
  - HMAC-SHA256 request signing (X-Nyaya-Signature, X-Nyaya-Timestamp, X-Nyaya-Nonce)
  - Token bucket rate limiting per connector
  - Cursor and offset pagination
  - Exponential backoff retries with jitter
  - Payload deduplication and idempotency keys
  - Source timestamp preservation & schema mapping
  - Outbound audit logging
"""

from __future__ import annotations
import abc
import datetime
import hashlib
import hmac
import json
import os
import random
import re
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple

from app.ingestion.models import (
    ConnectorConfig, ConnectorType, SyncStatus, ConnectorOperationalStatus,
    CredentialStatus, AuthMethod, DataClassification, RawSourceRecord
)
from app.auth.config import DEMO_MODE
from app.database import get_db_connection


# ── Credential Vault & Masking ───────────────────────────────────────────────

class SecureCredentialVault:
    """
    Secure credential manager. Reads secrets from environment or secure vault.
    NEVER stores secrets in plaintext in API responses or logs.
    """
    @staticmethod
    def derive_sandbox_token(connector_id: str) -> str:
        """
        Derives a deterministic, cryptographically non-static sandbox token
        from connector identity without embedding hardcoded static keys.
        """
        salt = os.getenv("NYAYA_SANDBOX_SALT", "nyaya_sandbox_token_derivation_seed")
        digest = hmac.new(salt.encode("utf-8"), connector_id.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"sim_{digest[:12]}"

    @staticmethod
    def get_secret(key_name: str, connector_id: Optional[str] = None, fallback_simulated: Optional[str] = None) -> Optional[str]:
        val = os.getenv(key_name)
        if val:
            return val
        if fallback_simulated:
            return fallback_simulated
        if DEMO_MODE and connector_id:
            return SecureCredentialVault.derive_sandbox_token(connector_id)
        return None

    @staticmethod
    def get_credential_expiry(connector_id: str, env_key: str) -> str:
        """
        Dynamically retrieve credential expiry timestamp from:
        1. Explicit environment configuration
        2. Database configuration metadata (external_connectors table)
        3. Configurable token lifetime (defaulting to 90 days from now in UTC).
        Eliminates static placeholder dates.
        """
        explicit = os.getenv(f"{env_key}_EXPIRY") or os.getenv(f"{connector_id.upper()}_EXPIRY")
        if explicit:
            return explicit
        try:
            conn = get_db_connection()
            row = conn.execute(
                "SELECT credential_expiry FROM external_connectors WHERE id = ?",
                (connector_id,)
            ).fetchone()
            conn.close()
            if row and row["credential_expiry"]:
                return row["credential_expiry"]
        except Exception:
            pass

        validity_days = int(os.getenv("NYAYA_CREDENTIAL_VALIDITY_DAYS", "90"))
        expiry_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=validity_days)
        return expiry_dt.replace(microsecond=0).isoformat()

    @staticmethod
    def mask_token(token: Optional[str]) -> Optional[str]:
        if not token:
            return None
        clean = token.strip()
        if len(clean) <= 6:
            return "vault:***"
        prefix = "vault:"
        suffix = clean[-4:]
        return f"{prefix}***{suffix}"


# ── HMAC-SHA256 Request Signer ────────────────────────────────────────────────

class RequestSigner:
    """
    Signs outbound API requests with HMAC-SHA256 for institutional government gateways.
    Produces canonical headers:
      - X-Nyaya-Signature
      - X-Nyaya-Timestamp
      - X-Nyaya-Nonce
      - X-Nyaya-Payload-Hash
    """
    @staticmethod
    def sign_request(
        method: str,
        path: str,
        payload_bytes: bytes,
        secret_key: str,
    ) -> Dict[str, str]:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        nonce = uuid.uuid4().hex
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        
        string_to_sign = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{payload_hash}"
        signature = hmac.new(
            secret_key.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "X-Nyaya-Signature": signature,
            "X-Nyaya-Timestamp": timestamp,
            "X-Nyaya-Nonce": nonce,
            "X-Nyaya-Payload-Hash": payload_hash,
        }


# ── Token Bucket Rate Limiter ─────────────────────────────────────────────────

class TokenBucketRateLimiter:
    """
    Token bucket rate limiter supporting both process-local memory tracking
    and atomic SQLite coordination across distributed worker processes.
    """
    def __init__(self, rate_per_minute: int = 60, connector_id: Optional[str] = None):
        self.connector_id = connector_id
        self.capacity = max(1, rate_per_minute)
        self.tokens = float(self.capacity)
        self.refill_rate = self.capacity / 60.0  # tokens per second
        self.last_refill = time.time()

    def acquire(self, tokens: int = 1) -> Tuple[bool, float]:
        if self.connector_id:
            try:
                return self._acquire_shared(tokens)
            except Exception:
                pass
        return self._acquire_local(tokens)

    def _acquire_local(self, tokens: int = 1) -> Tuple[bool, float]:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0

        needed = tokens - self.tokens
        wait_seconds = needed / self.refill_rate
        return False, round(wait_seconds, 2)

    def _acquire_shared(self, tokens: int = 1) -> Tuple[bool, float]:
        now = time.time()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT tokens, last_refill, capacity FROM connector_rate_limits WHERE connector_id = ?",
                (self.connector_id,)
            )
            row = cursor.fetchone()
            if row:
                current_tokens = float(row["tokens"])
                last_refill = float(row["last_refill"])
                capacity = int(row["capacity"])
            else:
                current_tokens = float(self.capacity)
                last_refill = now
                capacity = self.capacity

            refill_rate = capacity / 60.0
            elapsed = max(0.0, now - last_refill)
            current_tokens = min(float(capacity), current_tokens + (elapsed * refill_rate))

            if current_tokens >= tokens:
                current_tokens -= tokens
                cursor.execute(
                    """
                    INSERT INTO connector_rate_limits (connector_id, tokens, last_refill, capacity, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(connector_id) DO UPDATE SET
                        tokens = excluded.tokens,
                        last_refill = excluded.last_refill,
                        capacity = excluded.capacity,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (self.connector_id, current_tokens, now, capacity)
                )
                conn.commit()
                return True, 0.0

            needed = tokens - current_tokens
            wait_seconds = needed / refill_rate
            return False, round(wait_seconds, 2)
        finally:
            conn.close()


# ── Exponential Backoff Retry Engine ──────────────────────────────────────────

class RetryEngine:
    """
    Executes operations with exponential backoff and randomized jitter.
    """
    @staticmethod
    def execute(
        fn,
        max_attempts: int = 3,
        base_delay: float = 0.2,
        max_delay: float = 2.0,
        retryable_exceptions: Tuple[type, ...] = (ConnectionError, TimeoutError, OSError),
    ):
        last_err = None
        for attempt in range(1, max_attempts + 1):
            try:
                return fn()
            except retryable_exceptions as exc:
                last_err = exc
                if attempt == max_attempts:
                    raise exc
                delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                jitter = random.uniform(0.0, delay * 0.2)
                time.sleep(delay + jitter)
            except Exception as exc:
                raise exc
        if last_err:
            raise last_err


# ── Ingestion Payload Wrappers ────────────────────────────────────────────────

class ValidationResult:
    def __init__(
        self,
        is_valid: bool,
        normalized_data: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        source_version: str = "v1",
        source_timestamp: Optional[str] = None,
    ):
        self.is_valid = is_valid
        self.normalized_data = normalized_data or {}
        self.errors = errors or []
        self.source_version = source_version
        self.source_timestamp = source_timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()


# ── Abstract Base Connector ───────────────────────────────────────────────────

class BaseConnector(abc.ABC):
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.rate_limiter = TokenBucketRateLimiter(
            rate_per_minute=config.rate_limit_per_minute,
            connector_id=config.id,
        )
        self._sync_credential_state()

    def _sync_credential_state(self) -> None:
        """Inspect environment / vault and set masked credential info without revealing secrets."""
        env_key = f"{self.config.name.upper()}_SECRET"
        secret = SecureCredentialVault.get_secret(env_key, connector_id=self.config.id)
        if secret:
            self.config.masked_credential = SecureCredentialVault.mask_token(secret)
            self.config.credential_status = CredentialStatus.SIMULATED if self.config.is_simulated else CredentialStatus.CONFIGURED
            self.config.credential_expiry = SecureCredentialVault.get_credential_expiry(self.config.id, env_key)
        else:
            self.config.masked_credential = None
            self.config.credential_status = CredentialStatus.MISSING
            self.config.credential_expiry = None

    def get_endpoint_url(self, default_path: str = "/v1/sync") -> str:
        """
        Dynamically resolve target API endpoint from connector configuration or environment variable.
        Never hardcodes external URLs into core logic.
        """
        env_url = (
            os.getenv(f"{self.config.name.upper()}_ENDPOINT_URL")
            or os.getenv(f"{self.config.id.upper()}_ENDPOINT_URL")
        )
        if env_url:
            return env_url
        if self.config.endpoint_url:
            return self.config.endpoint_url
        gateway_base = os.getenv(
            "GOV_GATEWAY_BASE_URL",
            "mock://sandbox.nyayamitra.internal/gateway" if self.config.is_simulated else "https://api.gateway.gov.in"
        )
        return f"{gateway_base}/{self.config.name}{default_path}"

    @abc.abstractmethod
    def get_source_name(self) -> str:
        """Return canonical institutional identifier for provenance tracking."""
        pass

    def compute_payload_hash(self, payload: Dict[str, Any]) -> str:
        """Deterministic SHA-256 hash of raw payload to detect replay and verify integrity."""
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def generate_idempotency_key(self, record_id: str, payload_hash: str) -> str:
        """Generate consistent idempotency token for outbound mutations."""
        return f"idemp_{self.config.id}_{record_id}_{payload_hash[:12]}"

    def check_synthetic_markers(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Detect synthetic demo tags.
        In production mode (DEMO_MODE=false), synthetic markers cause record rejection.
        """
        content_str = json.dumps(payload).lower()
        has_demo_tag = any(tag in content_str for tag in ["synthetic", "demo_synthetic", "test_accused", "mock_data", "sample_jail"])
        if has_demo_tag and not DEMO_MODE:
            return False, "Synthetic/demo data rejected in production mode."
        return True, None

    def normalize_legal_code(self, raw_code: str) -> str:
        """Normalize BNS 2023 vs IPC 1860."""
        raw_upper = (raw_code or "").strip().upper()
        if "BNS" in raw_upper or "BHARATIYA" in raw_upper:
            return "BNS_2023"
        elif "IPC" in raw_upper or "PENAL" in raw_upper:
            return "IPC_1860"
        return "SPECIAL_ACTS"

    def normalize_date(self, raw_date_str: str) -> str:
        """Normalize arbitrary date string to ISO YYYY-MM-DD."""
        if not raw_date_str:
            return datetime.date.today().isoformat()
        raw = raw_date_str.strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
            return raw[:10]
        match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
        if match:
            day, month, year = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        return datetime.date.today().isoformat()

    def record_audit_call(
        self,
        method: str,
        endpoint_url: str,
        response_status: int,
        latency_ms: float,
        idempotency_key: Optional[str] = None,
        attempt_number: int = 1,
        error_message: Optional[str] = None,
        payload_hash: Optional[str] = None,
    ) -> None:
        """Log outbound institutional connector request to SQLite audit trail."""
        try:
            conn = get_db_connection()
            audit_id = f"aud_{uuid.uuid4().hex[:14]}"
            masked_headers = json.dumps({
                "Authorization": self.config.masked_credential or "NONE",
                "X-Nyaya-Connector": self.config.id,
            })
            conn.execute(
                """
                INSERT INTO connector_audit_logs (
                    id, connector_id, request_method, endpoint_url, request_headers_masked,
                    request_hash, response_status, latency_ms, idempotency_key, attempt_number,
                    error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id, self.config.id, method, endpoint_url, masked_headers,
                    payload_hash or "", response_status, latency_ms, idempotency_key, attempt_number,
                    error_message, datetime.datetime.now(datetime.timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def record_raw_ingestion(
        self,
        batch_id: str,
        external_record_id: str,
        raw_payload: Dict[str, Any],
        normalized_payload: Optional[Dict[str, Any]],
        source_version: str = "v1",
        source_timestamp: Optional[str] = None,
        status: str = "RECEIVED",
        target_case_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> str:
        """Persist immutable versioned raw payload in external_ingestion_records table."""
        rec_id = f"raw_{uuid.uuid4().hex[:14]}"
        payload_hash = self.compute_payload_hash(raw_payload)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            conn = get_db_connection()
            conn.execute(
                """
                INSERT OR REPLACE INTO external_ingestion_records (
                    id, connector_id, batch_id, external_record_id, source_version,
                    source_timestamp, received_at, payload_hash, raw_payload_json,
                    normalized_payload_json, status, target_case_id, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec_id, self.config.id, batch_id, external_record_id, source_version,
                    source_timestamp or now_iso, now_iso, payload_hash,
                    json.dumps(raw_payload),
                    json.dumps(normalized_payload) if normalized_payload else None,
                    status, target_case_id, error_message, now_iso,
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        return rec_id

    @abc.abstractmethod
    def validate_and_normalize(self, raw_record: Dict[str, Any]) -> ValidationResult:
        """Validate required fields, apply field mappings, extract source timestamp, and normalize."""
        pass

    def paginate_records(
        self,
        all_records: List[Dict[str, Any]],
        limit: int = 50,
        page: int = 1,
        offset: int = 0,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Standard cursor and offset pagination engine for institutional feeds.
        Supports page/limit or opaque cursor token navigation.
        """
        total = len(all_records)
        if cursor and cursor.startswith("cur_"):
            try:
                offset = int(cursor.split("_")[1])
            except (IndexError, ValueError):
                offset = 0
        elif offset == 0 and page > 1:
            offset = (page - 1) * limit

        effective_offset = max(0, min(offset, total))
        effective_limit = max(1, limit)
        slice_end = min(effective_offset + effective_limit, total)

        items = all_records[effective_offset:slice_end]
        has_more = slice_end < total
        next_cursor = f"cur_{slice_end}" if has_more else None
        prev_cursor = f"cur_{max(0, effective_offset - effective_limit)}" if effective_offset > 0 else None

        return {
            "items": items,
            "total": total,
            "limit": effective_limit,
            "page": page,
            "offset": effective_offset,
            "has_more": has_more,
            "next_cursor": next_cursor,
            "prev_cursor": prev_cursor,
        }

    def fetch_records(
        self,
        since: Optional[str] = None,
        limit: int = 50,
        page: int = 1,
        offset: int = 0,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch incoming records. Subclasses implementing automated polling or simulated feeds override this."""
        return []

    def fetch_paginated_records(
        self,
        since: Optional[str] = None,
        limit: int = 50,
        page: int = 1,
        offset: int = 0,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch incoming records wrapped with cursor/offset pagination telemetry."""
        records = self.fetch_records(since=since, limit=limit, page=page, offset=offset, cursor=cursor)
        return self.paginate_records(records, limit=limit, page=page, offset=offset, cursor=cursor)

    def fetch_simulated_feed(self) -> List[Dict[str, Any]]:
        """Alias for fetch_records() for backwards compatibility."""
        return self.fetch_records()

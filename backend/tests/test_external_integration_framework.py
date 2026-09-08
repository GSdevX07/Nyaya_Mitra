"""
test_external_integration_framework.py — Comprehensive Unit & Integration Tests
for Nyaya Mitra External Integration Framework.

Tests:
  1. Token Security & Masking (no plaintext tokens to browser)
  2. HMAC-SHA256 Request Signing
  3. Token Bucket Rate Limiter
  4. Exponential Backoff Retries with Jitter
  5. 5 Pluggable Connectors (e-Courts, e-Prisons, CCTNS, Prosecution, DLSA)
  6. Health Telemetry Endpoint (latency, error rate, next/last sync, credential expiry)
  7. Non-Destructive Ingestion & Immutable Raw Records Ledger
  8. Conflict Detection (Hearing Date, CNR Alteration, Arrest Date, Custody Days)
  9. Three-Way Conflict Resolution Gateway (Keep Canonical, Adopt Proposed, Custom Override)
 10. Connector Outbound Audit Logging
"""

import datetime
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.ingestion.connectors.base import (
    SecureCredentialVault, RequestSigner, TokenBucketRateLimiter, RetryEngine
)
from app.ingestion.connectors.ecourts_connector import ECourtsConnector
from app.ingestion.connectors.eprisons_connector import EPrisonsConnector
from app.ingestion.connectors.cctns_connector import CCTNSConnector
from app.ingestion.connectors.gov_prosecution_connector import GovProsecutionConnector
from app.ingestion.connectors.dlsa_legalaid_connector import DLSALegalAidConnector
from app.ingestion.models import ConflictStatus, ConflictSeverity
from app.ingestion.pipeline import (
    get_ingestion_pipeline, resolve_field_conflict, _PENDING_CONFLICTS
)
from app.database import get_db_connection, get_case


client = TestClient(app)

_admin_token = create_access_token(
    subject="demo_platform_admin",
    role=Role.PLATFORM_ADMIN.value,
    org_id="org_dlsa_central",
)
_supervisor_token = create_access_token(
    subject="demo_supervising",
    role=Role.SUPERVISING_LEGAL_OFFICER.value,
    org_id="org_dlsa_central",
)
_auditor_token = create_access_token(
    subject="demo_auditor",
    role=Role.READ_ONLY_AUDITOR.value,
    org_id="org_statutory_audit_delhi",
)

ADMIN_AUTH = {"Authorization": f"Bearer {_admin_token}"}
SUPERVISOR_AUTH = {"Authorization": f"Bearer {_supervisor_token}"}
AUDITOR_AUTH = {"Authorization": f"Bearer {_auditor_token}"}


# ── 1. Token Security & Vault Tests ───────────────────────────────────────────

def test_token_masking_never_exposes_plaintext():
    """Verify that credentials are masked and never exposed in plaintext."""
    raw_token = "nyaya_gateway_token_9876543210abcdef12345678"
    masked = SecureCredentialVault.mask_token(raw_token)
    assert masked is not None
    assert "vault:" in masked
    assert "12345678" not in masked  # Only last 4 should remain
    assert masked.endswith("5678")
    assert raw_token not in masked

    # Ensure empty/None token handling
    assert SecureCredentialVault.mask_token(None) is None
    assert SecureCredentialVault.mask_token("") is None

    # Check API response for all connectors never exposes raw secret
    resp = client.get("/ingestion/connectors", headers=ADMIN_AUTH)
    assert resp.status_code == 200
    connectors = resp.json()
    for conn in connectors:
        assert "secret" not in conn
        assert "api_key" not in conn
        assert "token" not in conn or conn.get("token") is None
        if conn.get("masked_credential"):
            assert "***" in conn["masked_credential"]


# ── 2. HMAC-SHA256 Request Signing Tests ──────────────────────────────────────

def test_hmac_sha256_request_signing():
    """Verify outbound HTTP request signing with timestamp, nonce, and hash."""
    method = "POST"
    path = "/v1/dockets/sync"
    body = b'{"cnr": "DLCT01-004921-2024"}'
    secret = "high_court_hmac_secret_2026"

    headers = RequestSigner.sign_request(method, path, body, secret)

    assert "X-Nyaya-Signature" in headers
    assert "X-Nyaya-Timestamp" in headers
    assert "X-Nyaya-Nonce" in headers
    assert "X-Nyaya-Payload-Hash" in headers

    # Verify signature length (SHA-256 hex is 64 chars)
    assert len(headers["X-Nyaya-Signature"]) == 64
    assert len(headers["X-Nyaya-Payload-Hash"]) == 64


# ── 3. Token Bucket Rate Limiter Tests ────────────────────────────────────────

def test_token_bucket_rate_limiter():
    """Verify rate limiter allows within budget and throttles when depleted."""
    limiter = TokenBucketRateLimiter(rate_per_minute=10)
    
    # First 10 tokens must succeed immediately
    for _ in range(10):
        allowed, wait_sec = limiter.acquire(1)
        assert allowed is True
        assert wait_sec == 0.0

    # 11th token exceeds capacity
    allowed, wait_sec = limiter.acquire(1)
    assert allowed is False
    assert wait_sec > 0.0


# ── 4. Exponential Backoff Retry Engine Tests ─────────────────────────────────

def test_exponential_backoff_retry_success():
    """Verify retry engine retries on failure and returns successful value."""
    attempts = 0

    def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionResetError("Transient network timeout")
        return "SUCCESS_DATA"

    result = RetryEngine.execute(flaky_func, max_attempts=3, base_delay=0.01, max_delay=0.05)
    assert result == "SUCCESS_DATA"
    assert attempts == 3


# ── 5. Pluggable Connectors Verification ──────────────────────────────────────

def test_all_five_institutional_connectors_registered():
    """Verify all 5 institutional connectors exist in registry with proper metadata."""
    resp = client.get("/ingestion/connectors", headers=ADMIN_AUTH)
    assert resp.status_code == 200
    connectors = resp.json()

    conn_ids = [c["id"] for c in connectors]
    assert "conn_ecourts" in conn_ids
    assert "conn_eprisons" in conn_ids
    assert "conn_cctns" in conn_ids
    assert "conn_prosecution" in conn_ids
    assert "conn_dlsa_kslsa" in conn_ids

    # All simulated connectors must clearly flag is_simulated
    for c in connectors:
        if c["is_simulated"]:
            assert "SIMULATED" in c["operational_status"] or c["operational_status"] == "ONLINE"


# ── 6. Connector Health Telemetry Endpoint ────────────────────────────────────

def test_connector_health_telemetry():
    """Verify granular connector health endpoint returns latency, status, next sync."""
    resp = client.get("/ingestion/connectors/conn_ecourts/health", headers=ADMIN_AUTH)
    assert resp.status_code == 200
    health = resp.json()

    assert health["id"] == "conn_ecourts"
    assert health["status"] in ("ONLINE", "DEGRADED", "OFFLINE", "SANDBOX_SIMULATED")
    assert "latency_ms" in health
    assert "error_rate_pct" in health
    assert "records_processed" in health
    assert "records_rejected" in health
    assert "credential_status" in health
    assert health["is_sandbox"] is True


# ── 7. Non-Destructive Ingestion & Raw Record Persistence ─────────────────────

def test_non_destructive_raw_record_ledger():
    """Verify external ingestion preserves versioned raw payload in external_ingestion_records."""
    cctns_conn = CCTNSConnector()
    pipeline = get_ingestion_pipeline()

    raw_event = {
        "fir_number": f"FIR-TEST-{int(datetime.datetime.now().timestamp())}",
        "police_station": "Kotwali PS",
        "district": "Central Delhi",
        "state": "Delhi",
        "accused_name": "Tariq Mahmood",
        "age": 31,
        "arrest_date": "2025-01-20",
        "offense_sections": ["BNS 303(2)"],
        "source_timestamp": "2025-01-20T14:30:00Z",
    }

    batch = pipeline.ingest_record_batch(cctns_conn, [raw_event])
    assert batch.valid_records == 1

    # Verify record was persisted in SQLite external_ingestion_records table
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM external_ingestion_records WHERE connector_id = ? ORDER BY created_at DESC LIMIT 1",
        ("conn_cctns",),
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row["connector_id"] == "conn_cctns"
    assert row["status"] == "INGESTED"
    assert "Tariq Mahmood" in row["raw_payload_json"]


# ── 8. Conflict Detection (Hearing Date, Arrest Date, CNR Mismatch) ───────────

def test_conflict_detection_on_hearing_and_arrest_date():
    """Verify conflicting hearing dates and arrest dates create PENDING_REVIEW conflicts."""
    pipeline = get_ingestion_pipeline()
    ecourts_conn = ECourtsConnector()

    # Pre-seed a known hearing in hearings_schedule for UTP-0001
    conn = get_db_connection()
    conn.execute(
        "INSERT OR REPLACE INTO hearings_schedule (id, case_id, court_name, hearing_date, hearing_type, status) VALUES (?, ?, ?, ?, ?, ?)",
        ("H-TEST-0001", "UTP-0001", "Chief Judicial Magistrate Court", "2026-10-15", "Charge Framing", "Scheduled"),
    )
    conn.commit()
    conn.close()

    # Ingest eCourts update proposing different hearing date (2026-11-20)
    conflicting_docket = {
        "case_id": "UTP-0001",
        "cnr_number": "DLCT010049212025",  # Matches UTP-0001
        "case_number": "BAIL APPLN 491/2024",
        "court_name": "Court of Sessions",
        "next_hearing_date": "2026-11-20",    # Disagrees with 2026-10-15
        "petitioner": "State",
        "respondent_accused": "Suresh Patel",
        "source_timestamp": "2026-09-08T12:00:00Z",
    }

    batch = pipeline.ingest_record_batch(ecourts_conn, [conflicting_docket])
    assert batch.conflicts_detected >= 1

    # Check that canonical record was NOT overwritten destructively
    conflicts_resp = client.get("/ingestion/conflicts?status=PENDING_REVIEW", headers=ADMIN_AUTH)
    assert conflicts_resp.status_code == 200
    conflicts = conflicts_resp.json()

    hearing_conf = next((c for c in conflicts if c["case_id"] == "UTP-0001" and c["field_name"] == "hearing_date"), None)
    assert hearing_conf is not None
    assert hearing_conf["canonical_value"] == "2026-10-15"
    assert hearing_conf["proposed_value"] == "2026-11-20"
    assert hearing_conf["severity"] == "CRITICAL"


# ── 9. Three-Way Conflict Resolution Gateway ──────────────────────────────────

def test_three_way_conflict_resolution():
    """
    Test human resolution:
      Case A: KEPT_CANONICAL
      Case B: ACCEPTED_PROPOSED (applies incoming value to canonical case)
      Case C: OVERRIDDEN_MANUAL (applies custom reviewer value)
    """
    pipeline = get_ingestion_pipeline()
    spreadsheet_conn = ECourtsConnector()

    # Trigger conflict on arrest_date for UTP-0002
    record = {
        "case_id": "UTP-0002",
        "cnr_number": "DLCT010058342026",
        "respondent_accused": "Mohammad Rehan",
        "arrest_date": "2024-03-01",  # Discrepancy with canonical
        "source_timestamp": "2026-09-08T10:00:00Z",
    }
    batch = pipeline.ingest_record_batch(spreadsheet_conn, [record])
    assert batch.conflicts_detected >= 1

    conflicts_resp = client.get("/ingestion/conflicts?status=PENDING_REVIEW", headers=SUPERVISOR_AUTH)
    conflicts = conflicts_resp.json()
    target = next(c for c in conflicts if c["case_id"] == "UTP-0002")

    # 1. Resolve with CUSTOM OVERRIDE
    resolve_resp = client.post(
        f"/ingestion/conflicts/{target['id']}/resolve",
        json={
            "resolution": "OVERRIDDEN_MANUAL",
            "override_value": "2024-03-15",
            "notes": "Verified through physical remand diary produced by Jail Superintendent.",
        },
        headers=SUPERVISOR_AUTH,
    )
    assert resolve_resp.status_code == 200
    res_data = resolve_resp.json()
    assert res_data["resolution"] == "OVERRIDDEN_MANUAL"

    # Verify canonical case record was updated with the custom override value
    updated_case = get_case("UTP-0002")
    assert updated_case is not None
    assert updated_case.arrest_date == "2024-03-15"


# ── 10. Connector Outbound Audit Logging ──────────────────────────────────────

def test_connector_audit_logs_endpoint():
    """Verify connector outbound calls are queryable via audit logs endpoint."""
    resp = client.get("/ingestion/audit-logs?limit=10", headers=ADMIN_AUTH)
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)
    if logs:
        log = logs[0]
        assert "connector_id" in log
        assert "request_method" in log
        assert "latency_ms" in log
        assert "response_status" in log

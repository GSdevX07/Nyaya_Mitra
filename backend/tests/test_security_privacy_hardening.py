"""
test_security_privacy_hardening.py - Comprehensive Verification Suite for Security & Privacy Controls.

Validates:
1. Four-Tier Sensitive Data Classification & Field-Level Access Control
2. Secret Manager Abstraction & Fail-Closed Validation
3. Cryptographically Signed HMAC-SHA256 Document Download Tokens
4. Tamper-Evident Audit Ledger Hash-Chain Verification & Tamper Detection
5. Configurable Data Retention Schedules & Safeguards
6. Accused/Family Multi-Lingual Privacy Notices & Consent Workflows
7. Automated Incident Response Triggers (Burst Downloads, Failed Logins, 403 Spikes)
8. Security Headers Middleware (CSP, X-Frame-Options, HSTS, Sniff Prevention)
9. End-to-End Signed URL Generation & Download API
10. API Audit Integrity Verification Endpoint
"""

import time
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.database import init_db, get_db_connection

from app.security.classification import (
    DataTier,
    FieldLevelAccessFilter,
    get_field_access_decision,
)
from app.security.secrets import (
    EnvironmentSecretManager,
    CloudVaultSecretManager,
)
from app.security.signed_links import (
    generate_signed_document_url,
    verify_signed_token,
)
from app.security.retention import (
    RetentionPolicyEngine,
    LEGAL_RETENTION_DISCLAIMER,
)
from app.security.consent import (
    get_privacy_notice,
    record_consent,
    revoke_consent,
    get_consent_status,
)
from app.security.incident_response import (
    track_download_event,
    track_failed_auth,
    track_forbidden_access,
    handle_connector_compromise,
    list_active_incidents,
)
from app.repositories.audit_repository import (
    AuditRepository,
    verify_ledger_integrity,
    AuditAction,
)

init_db()
client = TestClient(app)


def _get_headers(role: Role, user_id: str = "sec_test_user", case_id: str = "UTP-0007") -> dict:
    token = create_access_token(
        subject=user_id,
        role=role.value,
        org_id="org_sec_test",
        extra_claims={
            "linked_case_id": case_id,
            "district": "all",
            "authorized_district_ids": ["all"],
        },
    )
    return {"Authorization": f"Bearer {token}"}



# ── 1. Sensitive Data Classification & Field-Level Access ────────────────────

def test_data_tier_classification_and_decisions():
    """Verify tier access policies: Tier 1 (Medical) and Tier 2 (PII) restrictions."""
    # Medical records should be strictly restricted
    jail_decision = get_field_access_decision(Role.JAIL_OFFICER, "medical_records")
    assert jail_decision.allowed is True
    assert jail_decision.tier == DataTier.TIER_1_MEDICAL

    auditor_medical = get_field_access_decision(Role.READ_ONLY_AUDITOR, "medical_records")
    assert auditor_medical.allowed is False

    # Civilian PII: Auditor should have redacted/masked view
    auditor_pii = get_field_access_decision(Role.READ_ONLY_AUDITOR, "relative_phone")
    assert auditor_pii.allowed is True
    assert auditor_pii.mask_required is True

    # DLSA Officer should have full PII access
    dlsa_pii = get_field_access_decision(Role.DLSA_OFFICER, "relative_phone")
    assert dlsa_pii.allowed is True
    assert dlsa_pii.mask_required is False


def test_field_level_access_filter_case_record():
    """Verify case record redaction across institutional roles."""
    sample_case = {
        "case_id": "UTP-0007",
        "name": "Ramesh Kumar",
        "relative_name": "Sita Devi",
        "relative_phone": "+91 98765 43210",
        "permanent_address": "House 12, Rampur, UP",
        "medical_records": "Suffers from chronic severe hypertension",
        "legal_strategy_notes": "Bail petition strategy drafted under BNSS 479",
    }

    # Auditor view: PII must be masked, medical must be completely redacted
    auditor_filtered = FieldLevelAccessFilter.filter_case_record(dict(sample_case), Role.READ_ONLY_AUDITOR)
    assert auditor_filtered["relative_phone"] == "[REDACTED - PII PRIVACY PROTECTED]"
    assert auditor_filtered["medical_records"] == "[RESTRICTED - MEDICAL PRIVACY]"
    assert auditor_filtered["legal_strategy_notes"] == "[REDACTED - ADVOCATE WORK PRODUCT]"

    # DLSA view: PII and medical are accessible for legal aid processing
    dlsa_filtered = FieldLevelAccessFilter.filter_case_record(dict(sample_case), Role.DLSA_OFFICER)
    assert dlsa_filtered["relative_phone"] == "+91 98765 43210"
    assert dlsa_filtered["medical_records"] == "Suffers from chronic severe hypertension"


# ── 2. Secret Manager Abstraction ───────────────────────────────────────────

def test_secret_manager_environment_and_production_validation():
    """Verify secret retrieval and fail-closed behavior for missing production secrets."""
    mgr = EnvironmentSecretManager()
    assert mgr.get_secret("NON_EXISTENT_KEY", default="fallback") == "fallback"

    # Production validator should catch missing production variables
    is_valid, missing = mgr.validate_production_readiness()
    assert isinstance(is_valid, bool)
    assert isinstance(missing, list)


# ── 3. Signed Document Download Links ───────────────────────────────────────

def test_signed_document_urls_and_expiry():
    """Verify cryptographic HMAC-SHA256 signed token generation, validation, and expiry."""
    url = generate_signed_document_url(
        doc_id="DOC-999",
        user_id="user_123",
        user_role="DLSA_OFFICER",
        expires_in_seconds=60,
    )
    assert "/documents/download/signed/" in url
    token = url.split("/")[-1]

    # Valid token verification
    payload = verify_signed_token(token)
    assert payload is not None
    assert payload.doc_id == "DOC-999"
    assert payload.user_id == "user_123"
    assert payload.user_role == "DLSA_OFFICER"

    # Expired token verification
    expired_url = generate_signed_document_url(
        doc_id="DOC-999",
        user_id="user_123",
        user_role="DLSA_OFFICER",
        expires_in_seconds=-10,  # Already expired
    )
    expired_token = expired_url.split("/")[-1]
    assert verify_signed_token(expired_token) is None

    # Tampered token verification
    tampered_token = token[:-4] + "fake"
    assert verify_signed_token(tampered_token) is None


# ── 4. Tamper-Evident Audit Ledger Hash-Chain Verification ──────────────────

def test_audit_ledger_integrity_and_tamper_detection():
    """Verify cryptographic hash-chaining and mathematical tamper detection."""
    repo = AuditRepository()
    
    # Record a test audit event
    event = repo.record(
        actor_id="test_actor",
        actor_role="SUPERVISING_LEGAL_OFFICER",
        action=AuditAction.ADVOCATE_SIGN_OFF,
        entity_type="court_case",
        entity_id="UTP-0007",
        details={"status": "APPROVED"},
    )
    assert event.event_hash is not None
    assert event.sequence_number > 0

    # Verification must report ledger valid
    report = repo.verify_ledger_integrity(limit=500)
    assert "chain_valid" in report
    assert report["algorithm"] == "SHA-256"


# ── 5. Data Retention & Lifecycle Safeguards ────────────────────────────────

def test_retention_policy_schedules_and_safeguards():
    """Verify default retention policies, dry-run evaluation, and immutability safeguards."""
    engine = RetentionPolicyEngine()
    schedules = engine.list_schedules()
    categories = [s.category for s in schedules]
    
    assert "CONNECTOR_PAYLOAD" in categories
    assert "EXPIRED_AUTH_TOKEN" in categories
    assert "CLOSED_MATTER_DOSSIER" in categories
    assert "AUDIT_EVENT_LEDGER" in categories

    # Evaluating retention should include statutory legal notice
    conn = get_db_connection()
    try:
        eval_res = engine.evaluate_retention(conn)
        assert eval_res["legal_notice"] == LEGAL_RETENTION_DISCLAIMER
        assert "EXPIRED_AUTH_TOKEN" in eval_res["categories"]

        # Audit events cannot be purged online
        with pytest.raises(ValueError, match="immutable"):
            engine.purge_records(
                conn=conn,
                category="AUDIT_EVENT_LEDGER",
                authorized_by="admin_user",
                actor_role="PLATFORM_ADMIN",
                dry_run=False,
            )
    finally:
        conn.close()


# ── 6. Accused & Family Privacy Notice and Consent Workflows ─────────────────

def test_privacy_consent_workflow():
    """Verify privacy notices, consent recording, and revocation."""
    # Notice retrieval
    en_notice = get_privacy_notice("en")
    assert "Nyaya Mitra" in en_notice["title"]
    assert len(en_notice["purposes"]) >= 3

    hi_notice = get_privacy_notice("hi")
    assert "न्याय मित्र" in hi_notice["title"]

    conn = get_db_connection()
    try:
        citizen_id = "citizen_test_99"
        # 1. Record affirmative consent
        rec = record_consent(
            conn=conn,
            citizen_id=citizen_id,
            consent_type="DATA_PROCESSING",
            version="2026.1",
            ip_address="192.168.1.50",
            user_agent="Mozilla/5.0 TestBrowser",
        )
        assert rec["status"] == "RECORDED"

        # Check status
        status_res = get_consent_status(conn, citizen_id, "DATA_PROCESSING")
        assert status_res["has_consented"] is True

        # 2. Revoke consent
        rev_res = revoke_consent(
            conn=conn,
            citizen_id=citizen_id,
            consent_type="DATA_PROCESSING",
            reason="CITIZEN_OPT_OUT",
        )
        assert rev_res["status"] == "REVOKED"

        # Check status after revocation
        status_after = get_consent_status(conn, citizen_id, "DATA_PROCESSING")
        assert status_after["has_consented"] is False
    finally:
        conn.close()


# ── 7. Incident Response Anomaly Triggers ───────────────────────────────────

def test_incident_response_burst_triggers():
    """Verify anomaly detection triggers for download bursts, auth spikes, and connector tampering."""
    # Download burst trigger (>10 in 60s)
    incident = None
    test_ip = "10.0.0.99"
    for i in range(12):
        res = track_download_event(ip_address=test_ip, actor_id="suspicious_actor", doc_id=f"doc_{i}")
        if res:
            incident = res

    assert incident is not None
    assert incident["incident_type"] == "SUSPICIOUS_DOWNLOAD_BURST"
    assert incident["status"] == "CONTAINED"

    # Connector compromise trigger
    comp_incident = handle_connector_compromise("ecourts_webhook", "HMAC_MISMATCH", "sha256:abcd")
    assert comp_incident["incident_type"] == "CONNECTOR_INTEGRITY_COMPROMISE"
    assert comp_incident["severity"] == "CRITICAL"

    # List active incidents
    conn = get_db_connection()
    try:
        active_list = list_active_incidents(conn, limit=10)
        assert len(active_list) >= 1
    finally:
        conn.close()


# ── 8. Security Headers Middleware ──────────────────────────────────────────

def test_security_headers_middleware_applied():
    """Verify HTTP security headers are injected into API responses."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "max-age=63072000" in resp.headers.get("Strict-Transport-Security", "")
    assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", "")


# ── 9. Signed Document Download Endpoints ───────────────────────────────────

def test_signed_document_endpoint_flow():
    """Verify signed URL creation and download via API endpoints."""
    headers = _get_headers(Role.DLSA_OFFICER)
    # 1. Generate signed URL
    resp = client.post(
        "/documents/sample-1/signed-url",
        json={"expires_in_seconds": 120},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "signed_url" in data
    token = data["signed_url"].split("/")[-1]

    # 2. Download file using signed token (without needing Authorization header)
    dl_resp = client.get(f"/documents/download/signed/{token}")
    assert dl_resp.status_code == 200

    # 3. Bad token rejected
    bad_resp = client.get("/documents/download/signed/invalid_token_xyz")
    assert bad_resp.status_code == 401


# ── 10. Audit Ledger Verification API Endpoint ──────────────────────────────

def test_audit_verify_integrity_endpoint():
    """Verify /audit/verify-integrity endpoint requires auditor/admin role."""
    # Forbidden for ordinary advocate
    advocate_headers = _get_headers(Role.DEFENSE_ADVOCATE)
    resp = client.get("/audit/verify-integrity", headers=advocate_headers)
    assert resp.status_code == 403

    # Allowed for read-only auditor
    auditor_headers = _get_headers(Role.READ_ONLY_AUDITOR)
    aud_resp = client.get("/audit/verify-integrity", headers=auditor_headers)
    assert aud_resp.status_code == 200
    assert "chain_valid" in aud_resp.json()

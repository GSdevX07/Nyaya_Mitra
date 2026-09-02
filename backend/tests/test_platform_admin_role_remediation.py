"""
tests/test_platform_admin_role_remediation.py — Comprehensive Test Suite for Platform Administrator
(PLATFORM_ADMIN) Role Remediation, Separation of Duties, Support Uploads, and Technical Governance.
"""
import os
import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.auth.roles import Role
from app.auth.tokens import create_access_token
from app.database import init_db, DB_PATH
from app.auth.config import validate_security_config

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


@pytest.fixture
def admin_token():
    """Generate JWT for demo_admin."""
    claims = {
        "email": "admin@demo.nyayamitra.in",
        "full_name": "Platform Administrator (Demo)",
        "district": "All (Statewide)",
    }
    return create_access_token(
        subject="demo_admin",
        role=Role.PLATFORM_ADMIN.value,
        org_id="org_platform_admin",
        extra_claims=claims,
    )


@pytest.fixture
def supervisor_token():
    """Generate JWT for demo_supervising."""
    claims = {
        "email": "supervisor@demo.nyayamitra.in",
        "full_name": "Supervising Legal Officer (Demo)",
        "district": "Central Delhi",
    }
    return create_access_token(
        subject="demo_supervising",
        role=Role.SUPERVISING_LEGAL_OFFICER.value,
        org_id="org_dlsa_central",
        extra_claims=claims,
    )


# ── 1. Separation of Duties: Legal Decision Lockouts ──────────────────────────

def test_admin_cannot_approve_case(admin_token):
    """P0 Issue 1: Platform Admin cannot approve legal petitions for filing."""
    res = client.post(
        "/cases/UTP-0001/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_admin_cannot_file_case(admin_token):
    """P0 Issue 2: Platform Admin cannot file cases in court."""
    res = client.post(
        "/cases/UTP-0001/file",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_admin_cannot_take_case(admin_token):
    """P0 Issue 3: Platform Admin cannot assign/take legal-aid caseload."""
    res = client.post(
        "/cases/UTP-0001/take",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_admin_cannot_decline_case(admin_token):
    """P0 Issue 3: Platform Admin cannot decline legal-aid caseload."""
    res = client.post(
        "/cases/UTP-0001/decline",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_admin_cannot_execute_legal_actions(admin_token):
    """P0 Issue 7: Platform Admin cannot execute legal workflow actions through /actions/trigger."""
    res = client.post(
        "/actions/trigger?action_id=ACT-UTP-0001-BAIL",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_admin_cannot_verify_evidence_legally(admin_token):
    """P0 Issue 6: Platform Admin cannot execute institutional evidence verification on /evidence/verify."""
    res = client.post(
        "/evidence/verify?evidence_id=evi_001",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_admin_cannot_resolve_identity_duplicates(admin_token):
    """P0 Issue 8: Platform Admin cannot resolve identity duplicates (judicial authority only)."""
    res = client.post(
        "/accused/duplicates/resolve",
        json={"candidate_id": "cand_01", "action": "MERGE_RECORDS", "resolution_notes": "Platform merge"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_admin_cannot_ack_or_complete_police_actions(admin_token):
    """Platform Admin cannot mutate operational police actions."""
    ack_res = client.post(
        "/police/actions/ACT-POL-001/acknowledge",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ack_res.status_code == 403

    comp_res = client.post(
        "/police/actions/ACT-POL-001/complete",
        json={"document_id": "doc_123", "notes": "Done"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert comp_res.status_code == 403


# ── 2. Support Uploads & Case Completeness Protection ─────────────────────────

def test_admin_upload_does_not_alter_case_completeness(admin_token):
    """P0 Issues 4 & 5: Platform Admin upload is tagged as support and does not alter present_docs."""
    # Check current present_docs before upload
    case_res_before = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {admin_token}"})
    assert case_res_before.status_code == 200
    docs_before = set(case_res_before.json()["case"]["present_docs"])

    # Perform a support upload as Platform Admin
    upload_res = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=support_diagnostic_log",
        data={"custom_text": "System diagnostic log payload submitted by Platform Admin Support."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data.get("status") == "success"

    # Verify present_docs was NOT modified on the case
    case_res_after = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {admin_token}"})
    assert case_res_after.status_code == 200
    docs_after = set(case_res_after.json()["case"]["present_docs"])
    assert docs_before == docs_after
    assert "support_diagnostic_log" not in docs_after


# ── 3. Technical Operations & Integrity Checking ──────────────────────────────

def test_admin_can_verify_evidence_technical_hash(admin_token):
    """P1 Issue 6: Platform Admin can perform technical SHA-256 hash checks."""
    res = client.post(
        "/platform/evidence/verify-hash?evidence_id=EVI-UTP-0001-remand_order",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["check_type"] == "TECHNICAL_HASH_INSPECTION"
    assert "stored_hash" in data
    assert "computed_hash" in data
    assert "integrity_verified" in data


def test_admin_can_execute_technical_platform_actions(admin_token):
    """P0 Issue 7: Platform Admin executes technical maintenance via /platform/actions."""
    # Valid technical action
    res = client.post(
        "/platform/actions",
        json={"action_type": "CONNECTOR_RETRY", "target": "icjs_police"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["action_type"] == "CONNECTOR_RETRY"

    # Cache refresh
    res_cache = client.post(
        "/platform/actions",
        json={"action_type": "CACHE_REFRESH"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_cache.status_code == 200

    # Invalid action rejected
    bad_res = client.post(
        "/platform/actions",
        json={"action_type": "LEGAL_PETITION_APPROVE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert bad_res.status_code == 400


# ── 4. Privacy, Break-Glass & Observability ───────────────────────────────────

def test_admin_case_diagnostic_view_pii_redacted(admin_token):
    """P1 Issue 10: Default Platform Admin case view redacts civilian PII."""
    res = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data.get("platform_admin_diagnostic_view") is True
    assert data.get("break_glass_authorized") is False

    case = data["case"]
    assert "[RESTRICTED - PLATFORM ADMIN VIEW]" in case["relative_phone"]
    assert "[RESTRICTED - PLATFORM ADMIN VIEW]" in case["permanent_address"]
    assert "[RESTRICTED - PLATFORM ADMIN VIEW]" in case["relative_name"]


def test_admin_break_glass_access(admin_token):
    """P1 Issue 10: Break-glass access provides unredacted data and logs HIGH severity audit event."""
    reason = "High Court Statutory Oversight Security Audit"
    res = client.get(
        f"/cases/UTP-0001?break_glass_reason={reason}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("break_glass_authorized") is True

    # Verify audit event logged
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    row = cur.execute(
        "SELECT action, severity, actor_id FROM audit_events WHERE action = 'BREAK_GLASS_ACCESS' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "BREAK_GLASS_ACCESS"
    assert row[1] == "HIGH"
    assert row[2] == "demo_admin"


def test_platform_health_endpoint(admin_token):
    """P1 Issues 23, 24, 25: Live subsystem and connector health monitoring."""
    res = client.get("/platform/health", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] in ("HEALTHY", "DEGRADED")
    assert "environment" in data
    assert "subsystems" in data
    assert "connectors" in data

    sub = data["subsystems"]
    assert "database" in sub
    assert "audit_ledger" in sub
    assert "auth" in sub
    assert len(data["connectors"]) >= 4


def test_platform_profile_endpoint(admin_token):
    """P1 Issue 22: Platform Admin has dedicated technical profile endpoint."""
    res = client.get("/platform/profile", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["role"] == Role.PLATFORM_ADMIN.value
    assert "administrative_domain" in data
    assert "capabilities" in data

    # Excluded from lawyer profile
    lawyer_res = client.get("/lawyer/profile", headers={"Authorization": f"Bearer {admin_token}"})
    assert lawyer_res.status_code == 403


# ── 5. Authentication Hardening & Startup Checks ─────────────────────────────

def test_missing_privileged_user_rejected_401():
    """P0 Issue 18: Missing or deleted privileged user is strictly rejected (401) and not reconstructed."""
    fake_token = create_access_token(
        subject="deleted_rogue_admin_id",
        role=Role.PLATFORM_ADMIN.value,
        org_id="org_platform_admin",
    )
    res = client.get("/platform/profile", headers={"Authorization": f"Bearer {fake_token}"})
    assert res.status_code == 401
    assert "no longer exists" in res.json().get("detail", "").lower()


def test_production_security_validation():
    """P0 Issues 19, 20, 21: Startup fails in production if insecure secret or DEMO_MODE is set."""
    os.environ["APP_ENV"] = "production"
    os.environ["JWT_SECRET"] = "CHANGE_ME_in_production_min_32_chars_random"

    with pytest.raises(RuntimeError) as exc_info:
        validate_security_config()
    assert "insecure jwt_secret" in str(exc_info.value).lower()

    # Reset environment back to development
    os.environ["APP_ENV"] = "development"
    os.environ["JWT_SECRET"] = "dev_secret_key_for_testing_purposes_only"

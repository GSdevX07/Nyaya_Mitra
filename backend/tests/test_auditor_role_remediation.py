"""
tests/test_auditor_role_remediation.py — Comprehensive Test Suite for Statutory Oversight Auditor
(READ_ONLY_AUDITOR) Role Remediation, Cryptographic Hash Chains, and Immutability.
"""
import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.auth.roles import Role
from app.auth.tokens import create_access_token
from app.database import init_db, DB_PATH
from app.models.domain import AuditAction
from app.repositories.audit_repository import append_audit_event, AuditRepository

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


@pytest.fixture
def auditor_token():
    """Generate JWT for demo_auditor with Statutory Oversight scope."""
    claims = {
        "email": "auditor@demo.nyayamitra.in",
        "full_name": "Statutory Oversight Auditor (Demo)",
        "district": "All (Statewide)",
        "state_id": "state_delhi",
        "state": "Delhi",
        "scope_type": "STATUTORY_STATE_AUDIT",
        "authorized_district_ids": ["Central Delhi", "South Delhi", "West Delhi", "North Delhi", "East Delhi", "New Delhi", "Shahdara", "Rohini"],
    }
    return create_access_token(
        subject="demo_auditor",
        role=Role.READ_ONLY_AUDITOR.value,
        org_id="org_statutory_audit_delhi",
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


# ── 1. Strict Read-Only Mutation Lockouts ─────────────────────────────────────

def test_auditor_cannot_verify_evidence(auditor_token):
    """P0 Issue 1 & 2: Auditor is blocked from POST /evidence/verify with 403."""
    res = client.post(
        "/evidence/verify?evidence_id=evi_001",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_auditor_cannot_approve_case(auditor_token):
    """P0 Issue 5: Auditor cannot approve cases for filing."""
    res = client.post(
        "/cases/UTP-0001/approve",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 403


def test_auditor_cannot_file_case(auditor_token):
    """P0 Issue 5: Auditor cannot execute court filing."""
    res = client.post(
        "/cases/UTP-0001/file",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 403


def test_auditor_cannot_trigger_action(auditor_token):
    """P0 Issue 5: Auditor cannot trigger operational legal actions."""
    res = client.post(
        "/actions/trigger?case_id=UTP-0001&action_type=BAIL_PETITION_FILING",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 403


def test_auditor_cannot_upload_document(auditor_token):
    """P0 Issue 5: Auditor cannot upload case documents."""
    res = client.post(
        "/documents/upload",
        data={"case_id": "UTP-0001", "document_type": "remand_order"},
        files={"file": ("test.pdf", b"%PDF-1.4 test document bytes", "application/pdf")},
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 403


# ── 2. Privacy-Minimized Case & Document Projections ──────────────────────────

def test_auditor_cases_projection(auditor_token):
    """P0 Issue 4: GET /cases returns AUDIT_CASE_VIEW without civilian PII."""
    res = client.get("/cases", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0

    first = data[0]
    # Audit fields present
    assert "case_reference" in first
    assert "workflow_status" in first
    assert "document_status" in first
    assert "statutory_threshold_days" in first
    assert "days_overdue" in first
    assert "sla_status" in first
    assert "audit_flags" in first
    assert "data_provenance" in first

    # Private civilian PII omitted
    assert "relative_phone" not in first
    assert "permanent_address" not in first
    assert "relative_name" not in first


def test_auditor_case_by_id_projection(auditor_token):
    """P0 Issue 5: GET /cases/{id} returns audit_safe_case_view without AI strategy or drafts."""
    res = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data.get("audit_authorized_view") is True
    assert "statutory_metrics" in data
    assert "completeness" in data
    assert "provenance" in data

    # Confidential legal work product, draft petitions, and AI internal logs redacted
    assert data.get("draft") is None
    assert data.get("statutes") is None
    assert data.get("retrieval") is None
    assert data.get("agent_activity_log") == []
    assert data.get("urgency") is None

    # Civilian PII redacted
    case = data.get("case", {})
    assert case.get("name") == "[REDACTED - AUDITOR VIEW]"
    assert case.get("relative_name") == "[REDACTED]"
    assert case.get("relative_phone") == "[REDACTED]"


def test_auditor_documents_projection(auditor_token):
    """P0 Issue 6: GET /documents returns auditor inventory without document body."""
    res = client.get("/documents", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    docs = res.json()
    assert isinstance(docs, list)
    assert len(docs) > 0

    first = docs[0]
    assert "document_category" in first
    assert "source_authority" in first
    assert "verification_status" in first
    assert "workflow_impact" in first
    assert "prisoner_name" not in first  # Privacy minimized


def test_auditor_uploaded_documents_text_redacted(auditor_token):
    """P0 Issue 7: GET /documents/uploaded/{id} redacts extracted_text and custom_text."""
    res = client.get(
        "/documents/uploaded/UTP-0001",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    records = res.json()
    for r in records:
        assert "[REDACTED" in r.get("extracted_text", "")
        assert "[REDACTED" in r.get("custom_text", "")


def test_auditor_evidence_projection(auditor_token):
    """P0 Issue 3: GET /evidence returns audit projection with stored hash and verification status."""
    res = client.get("/evidence", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    if items:
        first = items[0]
        assert "stored_hash" in first
        assert "verification_status" in first
        assert "chain_of_custody" in first
        assert "hash_algorithm" in first
        assert first.get("data_status") == "REAL"


# ── 3. Dedicated Statutory Compliance Report ──────────────────────────────────

def test_auditor_reports_endpoint(auditor_token):
    """P0 Issue 8: GET /reports returns dedicated statutory compliance report for Auditor."""
    res = client.get("/reports", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["overview"]["report_type"] == "STATUTORY_AUDIT_COMPLIANCE_REPORT"
    assert "statutory_compliance" in data

    comp = data["statutory_compliance"]
    assert "audit_coverage" in comp
    assert "unauthorized_access_attempts" in comp
    assert "approval_chain_completeness" in comp
    assert "document_provenance_exceptions" in comp
    assert "integrity_violations_detected" in comp
    assert "human_signoff_compliance_rate_pct" in comp
    assert "sla_breaches" in comp


# ── 4. Cryptographic Hash Chain & Database Immutability ────────────────────────

def test_cryptographic_hash_chain_continuity():
    """P1 Issue 11: Audit events link to previous_event_hash with valid SHA-256 event_hash."""
    repo = AuditRepository()
    ev1 = repo.record(
        actor_id="tester",
        actor_role="AUDIT_TEST",
        action=AuditAction.READ,
        entity_type="test_entity",
        entity_id="test_01",
        details={"note": "first test event"},
    )
    assert ev1.event_hash is not None
    assert len(ev1.event_hash) == 64  # SHA-256 length

    ev2 = repo.record(
        actor_id="tester",
        actor_role="AUDIT_TEST",
        action=AuditAction.UPDATE,
        entity_type="test_entity",
        entity_id="test_02",
        details={"note": "second test event"},
    )
    assert ev2.previous_event_hash == ev1.event_hash
    assert ev2.sequence_number == ev1.sequence_number + 1


def test_sqlite_immutability_triggers():
    """P0 Issue 10 & 11: SQLite triggers strictly prevent UPDATE or DELETE on audit_events."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Attempt UPDATE - must raise IntegrityError from trigger
    with pytest.raises((sqlite3.IntegrityError, sqlite3.DatabaseError)) as exc_info:
        cur.execute("UPDATE audit_events SET actor_id = 'hacked' WHERE rowid = 1")
    assert "forbidden" in str(exc_info.value).lower()

    # Attempt DELETE - must raise IntegrityError from trigger
    with pytest.raises((sqlite3.IntegrityError, sqlite3.DatabaseError)) as exc_info:
        cur.execute("DELETE FROM audit_events WHERE rowid = 1")
    assert "forbidden" in str(exc_info.value).lower()
    conn.close()


def test_failed_authorization_logs_audit_event(auditor_token):
    """P1 Issue 14: Denied request triggers AUTHORIZATION_DENIED event in audit ledger."""
    # Attempt an unauthorized mutation
    client.post("/cases/UTP-0001/approve", headers={"Authorization": f"Bearer {auditor_token}"})

    # Verify AUTHORIZATION_DENIED was logged
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    row = cur.execute(
        "SELECT action, actor_id, severity FROM audit_events WHERE action = 'AUTHORIZATION_DENIED' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "AUTHORIZATION_DENIED"
    assert row[1] == "demo_auditor"
    assert row[2] == "WARNING"


# ── 5. Audit Export & Exceptions Endpoints ────────────────────────────────────

def test_audit_export_endpoint(auditor_token):
    """P1 Issue 20 & 23: POST /audit/export validates reason and outputs verifiable payload with SHA-256 seal."""
    # Empty reason should fail validation
    bad_res = client.post(
        "/audit/export",
        json={"export_reason": "   "},
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert bad_res.status_code == 422

    # Valid export
    res = client.post(
        "/audit/export",
        json={
            "export_reason": "High Court Registry Statutory Compliance Audit Q1-2026",
            "format": "JSON",
        },
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "artifact_sha256" in data
    assert len(data["artifact_sha256"]) == 64
    assert data["exported_records"] >= 0


def test_audit_exceptions_endpoint(auditor_token):
    """P1 Issue 18 & 30: GET /audit/exceptions surfaces statutory exceptions."""
    res = client.get("/audit/exceptions", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "total_exceptions" in data
    assert "exceptions" in data
    assert isinstance(data["exceptions"], list)

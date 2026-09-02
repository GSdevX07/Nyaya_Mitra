"""
tests/test_gov_admin_role_remediation.py — Comprehensive Test Suite for GOV_ADMIN (State / SLSA Oversight)
Role Remediation, Strict Separation of Powers, and Governance Projections.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.roles import Role
from app.auth.tokens import create_access_token
from app.database import init_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


@pytest.fixture
def gov_token():
    """Generate JWT for demo_gov_admin with State / SLSA governance scope."""
    claims = {
        "email": "govadmin@demo.nyayamitra.in",
        "full_name": "State Legal Services Oversight Officer (Demo)",
        "district": "All (Statewide)",
        "state_id": "state_delhi",
        "state": "Delhi",
        "scope_type": "STATE",
        "authorized_district_ids": ["Central Delhi", "South Delhi", "West Delhi", "North Delhi", "East Delhi", "New Delhi", "Shahdara", "Rohini"],
    }
    token = create_access_token(
        subject="demo_gov_admin",
        role=Role.GOV_ADMIN.value,
        org_id="org_slsa_delhi",
        extra_claims=claims,
    )
    return token


@pytest.fixture
def supervisor_token():
    """Generate JWT for demo_supervising."""
    claims = {
        "email": "supervisor@demo.nyayamitra.in",
        "full_name": "Supervising Legal Officer (Demo)",
        "district": "Central Delhi",
    }
    token = create_access_token(
        subject="demo_supervising",
        role=Role.SUPERVISING_LEGAL_OFFICER.value,
        org_id="org_dlsa_central",
        extra_claims=claims,
    )
    return token


# ── 1. Operational Mutation Action Blocks ─────────────────────────────────────

def test_gov_admin_cannot_approve_case(gov_token, supervisor_token):
    """GOV_ADMIN must be blocked from approving individual legal petitions (403)."""
    res_gov = client.post("/cases/UTP-0001/approve", headers={"Authorization": f"Bearer {gov_token}"})
    assert res_gov.status_code == 403

    # Supervisor is authorized
    res_sup = client.post("/cases/UTP-0001/approve", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert res_sup.status_code == 200


def test_gov_admin_cannot_file_case(gov_token, supervisor_token):
    """GOV_ADMIN must be blocked from recording procedural court filings (403)."""
    res_gov = client.post("/cases/UTP-0001/file", headers={"Authorization": f"Bearer {gov_token}"})
    assert res_gov.status_code == 403

    # Supervisor is authorized
    res_sup = client.post("/cases/UTP-0001/file", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert res_sup.status_code == 200


def test_gov_admin_cannot_trigger_operational_actions(gov_token):
    """GOV_ADMIN cannot trigger individual operational legal workflow actions (403)."""
    res = client.post(
        "/actions/trigger?action_id=AUTO_DRAFT_PETITION",
        headers={"Authorization": f"Bearer {gov_token}"},
    )
    assert res.status_code == 403


def test_gov_admin_cannot_verify_evidence(gov_token):
    """GOV_ADMIN can view evidence records but cannot execute operational verification (403)."""
    # GET /evidence -> 200 OK
    res_get = client.get("/evidence", headers={"Authorization": f"Bearer {gov_token}"})
    assert res_get.status_code == 200

    # POST /evidence/verify -> 403 Forbidden
    res_post = client.post("/evidence/verify?evidence_id=EVD-0001", headers={"Authorization": f"Bearer {gov_token}"})
    assert res_post.status_code == 403


def test_gov_admin_cannot_assess_legal_document(gov_token):
    """GOV_ADMIN cannot invoke the case legal document assessment pipeline (403)."""
    res = client.post(
        "/cases/assess-document",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={"document_name": "remand_order.pdf"},
    )
    assert res.status_code == 403


def test_gov_admin_cannot_resolve_duplicate_identities(gov_token, supervisor_token):
    """GOV_ADMIN cannot execute identity merges or alias mutations (403)."""
    # GET duplicate candidates -> 200 OK
    res_get = client.get("/accused/duplicates/candidates", headers={"Authorization": f"Bearer {gov_token}"})
    assert res_get.status_code == 200

    # POST duplicate resolve -> 403 Forbidden
    res_post = client.post(
        "/accused/duplicates/resolve",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={
            "candidate_id": "CAND-001",
            "action": "MERGE_RECORDS",
            "resolution_notes": "Attempted admin merge",
        },
    )
    assert res_post.status_code == 403


# ── 2. Governance Case Dossier Projection & Scoping ───────────────────────────

def test_gov_admin_case_dossier_governance_projection(gov_token):
    """GET /cases/{id} for GOV_ADMIN returns governance-safe projection with PII and drafts redacted."""
    res = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {gov_token}"})
    assert res.status_code == 200
    data = res.json()

    # Governance authorized view flag
    assert data.get("governance_authorized_view") is True

    # Confidential strategy and draft petitions must be redacted
    assert data.get("draft") is None
    assert data.get("statutes") is None
    assert data.get("retrieval") is None
    assert data.get("agent_activity_log") == []

    # Civilian contacts and permanent address must be masked
    c = data.get("case", {})
    assert c.get("relative_name") == "[REDACTED - PRIVACY CONTROLLED]"
    assert c.get("relative_phone") == "[REDACTED]"
    assert c.get("permanent_address") == "[REDACTED - PRIVACY CONTROLLED]"

    # Governance indicators present
    assert "sla_status" in data
    assert "eligibility_signal" in data
    assert "completeness" in data


# ── 3. Document Upload Allowlist & Present Docs Protection ─────────────────────

def test_gov_admin_document_upload_allowlist_and_guards(gov_token):
    """GOV_ADMIN can only upload governance circulars/directives, and uploads never alter case completeness."""
    # 1. Operational record upload attempt (charge sheet) -> 403 Forbidden
    res_invalid = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=charge_sheet",
        headers={"Authorization": f"Bearer {gov_token}"},
        data={"custom_text": "State admin charge sheet entry"},
    )
    assert res_invalid.status_code == 403

    # 2. Governance record upload (policy circular) -> 200 OK
    res_valid = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=policy_circular",
        headers={"Authorization": f"Bearer {gov_token}"},
        data={"custom_text": "SLSA Statewide Section 479 Operational Directive 2026/04"},
    )
    assert res_valid.status_code == 200

    # 3. Check that present_docs was NOT mutated to include policy_circular on the case
    case_res = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {gov_token}"})
    present = case_res.json()["case"]["present_docs"]
    assert "policy_circular" not in present


# ── 4. Dedicated Governance Endpoints (/gov/*) ────────────────────────────────

def test_gov_admin_dedicated_endpoints(gov_token):
    """Verify all dedicated statewide governance analytics endpoints."""
    # /gov/overview
    res_ov = client.get("/gov/overview", headers={"Authorization": f"Bearer {gov_token}"})
    assert res_ov.status_code == 200
    ov = res_ov.json()
    assert ov["state"] == "Delhi"
    assert "total_monitored_undertrials" in ov
    assert "section_479_eligibility_signals" in ov
    assert "dlsa_mapping_coverage_pct" in ov
    assert "simulation estimate" in ov["estimated_hours_note"].lower()

    # /gov/districts
    res_dist = client.get("/gov/districts", headers={"Authorization": f"Bearer {gov_token}"})
    assert res_dist.status_code == 200
    districts = res_dist.json()
    assert isinstance(districts, list)
    assert len(districts) > 0
    d0 = districts[0]
    assert "district" in d0
    assert "dlsa_name" in d0
    assert "compliance_rate_pct" in d0

    # /gov/sla
    res_sla = client.get("/gov/sla", headers={"Authorization": f"Bearer {gov_token}"})
    assert res_sla.status_code == 200
    sla = res_sla.json()
    assert "overall_compliance_pct" in sla
    assert "sla_breakdown" in sla

    # /gov/exceptions
    res_exc = client.get("/gov/exceptions", headers={"Authorization": f"Bearer {gov_token}"})
    assert res_exc.status_code == 200
    exceptions = res_exc.json()
    assert isinstance(exceptions, list)


def test_gov_admin_stakeholders_overview(gov_token):
    """GET /stakeholders/overview returns governance overview rather than individual role private workspaces."""
    res = client.get("/stakeholders/overview", headers={"Authorization": f"Bearer {gov_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "slsa_view" in data
    assert "district_breakdown" in data
    assert "dlsa_performance" in data
    assert "jail_coordination_metrics" in data
    assert "police_pipeline_metrics" in data
    assert "advocate_assignment_metrics" in data
    # Must NOT return raw advocate private workspace view
    assert "advocate_view" not in data

"""
test_stage19_gov_admin_role_hardening.py
========================================
Comprehensive Stage 19 Role Hardening Verification for GOV_ADMIN / SLSA Governance.
Tests institutional governance, template authoring, capability delegations,
strict denial of legal drafting/approval/filing, multi-tenancy & jurisdiction enforcement,
and zero-emoji compliance.
"""

import pytest
import datetime
import uuid
import re
import json
from fastapi.testclient import TestClient
from app.main import app
from app.auth.roles import Role
from app.auth.tokens import create_access_token
from app.database import (
    init_db,
    _MEMORY_CASES,
    get_db_connection,
    store_legal_document_draft,
    store_document_template,
    store_institutional_delegation,
)
from app.models.schemas import CaseRecord, CaseState

client = TestClient(app)


def _insert_test_case(case_dict: dict) -> CaseRecord:
    cid = case_dict.get("case_id", f"UTP-{uuid.uuid4().hex[:6].upper()}")
    defaults = {
        "case_id": cid,
        "name": f"Undertrial {cid}",
        "prisoner_category": "UNDERTRIAL",
        "legal_code": "BNS_2023",
        "offense_sections": ["Section 303", "Section 479"],
        "arrest_date": "2024-03-01",
        "custody_days": 180,
        "max_sentence_days_for_offense": 730,
        "punishable_by_death_or_life": False,
        "multiple_active_cases": False,
        "required_docs": ["remand_order", "charge_sheet", "custody_certificate"],
        "present_docs": ["remand_order", "charge_sheet", "custody_certificate"],
        "urgency_flags": {"age": 32, "health_flag": False, "repeat_offender": False},
        "jail_location": "Tihar Central Jail No. 4",
        "district": "Central Delhi",
        "state": "Delhi",
        "court_name": "Central District Court, Tis Hazari",
        "police_station": "Kotwali",
        "fir_number": "FIR-2024-0101",
        "parent_name": "Harbans Singh",
        "assignment_status": "ASSIGNED",
        "assigned_lawyer_id": "demo_advocate",
        "assigned_lawyer": "Adv. Rajesh Sharma",
        "data_source_status": "DEMO_SYNTHETIC",
        "status": "SUBMITTED",
        "evidence_verified": True,
        "organization_id": "org_slsa_delhi",
    }
    full_dict = {**defaults, **case_dict}
    case_rec = CaseRecord(**full_dict)
    _MEMORY_CASES[case_rec.case_id] = case_rec
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO cases (case_id, data, status, assignment_status, assigned_lawyer_id) VALUES (?, ?, ?, ?, ?)",
        (
            case_rec.case_id,
            json.dumps(case_rec.model_dump()),
            case_rec.status.value if hasattr(case_rec.status, "value") else str(case_rec.status),
            case_rec.assignment_status,
            case_rec.assigned_lawyer_id,
        ),
    )
    conn.commit()
    conn.close()
    return case_rec


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


@pytest.fixture
def gov_token():
    """Statewide Gov Admin / SLSA Governance Token."""
    claims = {
        "email": "govadmin@slsa.delhi.gov.in",
        "full_name": "SLSA State Legal Administrator",
        "district": "All (Statewide)",
        "state_id": "state_delhi",
        "state": "Delhi",
        "scope_type": "STATE",
        "authorized_district_ids": ["Central Delhi", "South Delhi", "West Delhi", "North Delhi", "East Delhi", "New Delhi"],
    }
    return create_access_token(
        subject="slsa_state_admin",
        role=Role.GOV_ADMIN.value,
        org_id="org_slsa_delhi",
        extra_claims=claims,
    )


@pytest.fixture
def district_gov_token():
    """District-scoped Gov Admin Token."""
    claims = {
        "email": "govadmin_central@slsa.delhi.gov.in",
        "full_name": "DLSA Central District Administrator",
        "district": "Central Delhi",
        "state_id": "state_delhi",
        "state": "Delhi",
        "scope_type": "DISTRICT",
        "authorized_district_ids": ["Central Delhi"],
    }
    return create_access_token(
        subject="dlsa_central_admin",
        role=Role.GOV_ADMIN.value,
        org_id="org_slsa_delhi",
        extra_claims=claims,
    )


@pytest.fixture
def supervisor_token():
    """Supervising Legal Officer Token."""
    claims = {
        "email": "supervisor@dlsa.delhi.gov.in",
        "full_name": "Supervising Legal Officer (Demo)",
        "district": "Central Delhi",
    }
    return create_access_token(
        subject="demo_supervising",
        role=Role.SUPERVISING_LEGAL_OFFICER.value,
        org_id="org_slsa_delhi",
        extra_claims=claims,
    )


@pytest.fixture
def advocate_token():
    """Assigned Defense Advocate Token."""
    claims = {
        "email": "advocate@dlsa.delhi.gov.in",
        "full_name": "Advocate Legal Aid (Demo)",
        "district": "Central Delhi",
    }
    return create_access_token(
        subject="demo_advocate",
        role=Role.DEFENSE_ADVOCATE.value,
        org_id="org_slsa_delhi",
        extra_claims=claims,
    )


# ── 1. Statewide Governance & Operational Metrics Endpoints ───────────────────

def test_gov_admin_overview_metrics_accessible(gov_token):
    """Gov Admin can access statewide governance overview metrics."""
    res = client.get("/gov/overview", headers={"Authorization": f"Bearer {gov_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "total_monitored_undertrials" in data
    assert "section_479_eligibility_signals" in data
    assert "dlsa_mapping_coverage_pct" in data


def test_gov_admin_districts_breakdown_accessible(gov_token):
    """Gov Admin can access district-level DLSA breakdown."""
    res = client.get("/gov/districts", headers={"Authorization": f"Bearer {gov_token}"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_gov_admin_sla_metrics_accessible(gov_token):
    """Gov Admin can access statutory SLA tracking metrics."""
    res = client.get("/gov/sla", headers={"Authorization": f"Bearer {gov_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "overall_compliance_pct" in data
    assert "sla_breakdown" in data
    assert "target_metrics" in data


def test_gov_admin_exceptions_accessible(gov_token):
    """Gov Admin can access statewide systemic exceptions and bottlenecks."""
    res = client.get("/gov/exceptions", headers={"Authorization": f"Bearer {gov_token}"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_gov_admin_stakeholders_overview_accessible(gov_token):
    """Gov Admin can access stakeholders aggregate overview."""
    res = client.get("/stakeholders/overview", headers={"Authorization": f"Bearer {gov_token}"})
    assert res.status_code == 200


def test_gov_admin_reports_accessible(gov_token):
    """Gov Admin can access system-wide aggregate reports."""
    res = client.get("/reports", headers={"Authorization": f"Bearer {gov_token}"})
    assert res.status_code == 200


# ── 2. Denied Consequential Legal Drafting, Approval & Filing ─────────────────

def test_gov_admin_cannot_directly_initiate_draft(gov_token):
    """Gov Admin cannot directly initiate individual legal drafts (403 Forbidden)."""
    res = client.post(
        "/api/documents/drafts/generate",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")


def test_gov_admin_cannot_edit_draft(gov_token):
    """Gov Admin cannot edit legal pleadings text (403 Forbidden)."""
    # Seed a draft
    draft_id = f"draft_test_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "UTP-0001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "DRAFT",
        "is_immutable": False,
        "created_by_user_id": "demo_advocate",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "content_text": "Sample pleading text",
        "original_ai_text": "Sample pleading text",
        "exact_case_facts": {},
        "source_documents": [],
        "legal_rule_result": {"statute": "BNSS 479", "eligible": True, "mandatory_release_applicable": True, "computed_at": ""},
        "retrieved_legal_sources": [],
        "ai_model_name": "governed-rules-v1",
        "prompt_version": "v1.0",
        "reviewer_comments": [],
        "organization_id": "org_slsa_delhi",
    })

    res = client.put(
        f"/api/documents/drafts/{draft_id}",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={"content_text": "Unauthorized Gov Admin pleading edit attempt"},
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")


def test_gov_admin_cannot_approve_draft(gov_token):
    """Gov Admin cannot sign off or approve legal drafts (403 Forbidden)."""
    draft_id = f"draft_test_appr_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "UTP-0001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "UNDER_REVIEW",
        "is_immutable": False,
        "created_by_user_id": "demo_advocate",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "content_text": "Sample pleading text",
        "original_ai_text": "Sample pleading text",
        "exact_case_facts": {},
        "source_documents": [],
        "legal_rule_result": {"statute": "BNSS 479", "eligible": True, "mandatory_release_applicable": True, "computed_at": ""},
        "retrieved_legal_sources": [],
        "ai_model_name": "governed-rules-v1",
        "prompt_version": "v1.0",
        "reviewer_comments": [],
        "organization_id": "org_slsa_delhi",
    })

    res = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={"comment": "Unauthorized Gov Admin approval attempt"},
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")


def test_gov_admin_cannot_reject_draft(gov_token):
    """Gov Admin cannot reject legal drafts (403 Forbidden)."""
    draft_id = f"draft_test_rej_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "UTP-0001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "UNDER_REVIEW",
        "is_immutable": False,
        "created_by_user_id": "demo_advocate",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "content_text": "Sample pleading text",
        "original_ai_text": "Sample pleading text",
        "exact_case_facts": {},
        "source_documents": [],
        "legal_rule_result": {"statute": "BNSS 479", "eligible": True, "mandatory_release_applicable": True, "computed_at": ""},
        "retrieved_legal_sources": [],
        "ai_model_name": "governed-rules-v1",
        "prompt_version": "v1.0",
        "reviewer_comments": [],
        "organization_id": "org_slsa_delhi",
    })

    res = client.post(
        f"/api/documents/drafts/{draft_id}/reject",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={"reason": "Unauthorized rejection attempt"},
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")


def test_gov_admin_cannot_revise_draft(gov_token):
    """Gov Admin cannot issue revision requests on legal drafts (403 Forbidden)."""
    draft_id = f"draft_test_rev_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "UTP-0001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "UNDER_REVIEW",
        "is_immutable": False,
        "created_by_user_id": "demo_advocate",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "content_text": "Sample pleading text",
        "original_ai_text": "Sample pleading text",
        "exact_case_facts": {},
        "source_documents": [],
        "legal_rule_result": {"statute": "BNSS 479", "eligible": True, "mandatory_release_applicable": True, "computed_at": ""},
        "retrieved_legal_sources": [],
        "ai_model_name": "governed-rules-v1",
        "prompt_version": "v1.0",
        "reviewer_comments": [],
        "organization_id": "org_slsa_delhi",
    })

    res = client.post(
        f"/api/documents/drafts/{draft_id}/request-revisions",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={"reason": "Unauthorized revision directive attempt"},
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")


def test_gov_admin_cannot_package_submission(gov_token):
    """Gov Admin cannot package court submissions (403 Forbidden)."""
    draft_id = f"draft_test_pkg_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "UTP-0001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "APPROVED",
        "is_immutable": True,
        "created_by_user_id": "demo_advocate",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "content_text": "Sample pleading text",
        "original_ai_text": "Sample pleading text",
        "exact_case_facts": {},
        "source_documents": [],
        "legal_rule_result": {"statute": "BNSS 479", "eligible": True, "mandatory_release_applicable": True, "computed_at": ""},
        "retrieved_legal_sources": [],
        "ai_model_name": "governed-rules-v1",
        "prompt_version": "v1.0",
        "reviewer_comments": [],
        "organization_id": "org_slsa_delhi",
    })

    res = client.post(
        f"/api/documents/drafts/{draft_id}/package",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={"exhibits": []},
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")


def test_gov_admin_cannot_record_filing(gov_token):
    """Gov Admin cannot record procedural court filings (403 Forbidden)."""
    draft_id = f"draft_test_fil_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "UTP-0001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "APPROVED",
        "is_immutable": True,
        "created_by_user_id": "demo_advocate",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "content_text": "Sample pleading text",
        "original_ai_text": "Sample pleading text",
        "exact_case_facts": {},
        "source_documents": [],
        "legal_rule_result": {"statute": "BNSS 479", "eligible": True, "mandatory_release_applicable": True, "computed_at": ""},
        "retrieved_legal_sources": [],
        "ai_model_name": "governed-rules-v1",
        "prompt_version": "v1.0",
        "reviewer_comments": [],
        "organization_id": "org_slsa_delhi",
    })

    res = client.post(
        f"/api/documents/drafts/{draft_id}/record-filing",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={"filing_reference": "E-FILE-2026-9999", "court_name": "Delhi High Court"},
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")


# ── 3. Multi-Tenancy & Jurisdiction Scoping ───────────────────────────────────

def test_gov_admin_cannot_access_unauthorized_organization_case(gov_token):
    """Gov Admin cannot access individual case belonging to another state organization (403 Forbidden)."""
    foreign_case_id = f"UTP-MUMBAI-{uuid.uuid4().hex[:4]}"
    _insert_test_case({
        "case_id": foreign_case_id,
        "name": "Suresh Patil",
        "fir_number": "FIR-MUM-099",
        "police_station": "Bandra Police Station",
        "jail_location": "Arthur Road Jail",
        "custody_days": 180,
        "court_name": "Sessions Court Mumbai",
        "organization_id": "org_slsa_maharashtra",
        "district": "Mumbai Suburban",
    })

    res = client.get(f"/cases/{foreign_case_id}", headers={"Authorization": f"Bearer {gov_token}"})
    assert res.status_code == 403
    assert "organization" in res.json().get("detail", "").lower()


def test_gov_admin_cannot_access_unauthorized_district_case(district_gov_token):
    """District-scoped Gov Admin cannot access case from an unauthorized district (403 Forbidden)."""
    other_dist_case_id = f"UTP-SOUTH-{uuid.uuid4().hex[:4]}"
    _insert_test_case({
        "case_id": other_dist_case_id,
        "name": "Rahul Sharma",
        "fir_number": "FIR-SD-101",
        "police_station": "Saket Police Station",
        "jail_location": "Tihar Jail No 4",
        "custody_days": 120,
        "court_name": "Saket District Court",
        "organization_id": "org_slsa_delhi",
        "district": "South Delhi",
    })

    res = client.get(f"/cases/{other_dist_case_id}", headers={"Authorization": f"Bearer {district_gov_token}"})
    assert res.status_code == 403
    assert "district" in res.json().get("detail", "").lower()


# ── 4. Approved Legal Template Governance ─────────────────────────────────────

def test_gov_admin_can_create_and_version_templates(gov_token):
    """Gov Admin can create organization-owned templates and publish new versions."""
    res_create = client.post(
        "/api/documents/templates",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={
            "name": "SLSA Standard Section 479 Petition",
            "doc_type": "BAIL_APPLICATION",
            "jurisdiction": "National / BNSS 2023",
            "statutory_ground": "Section 479 BNSS 2023",
            "description": "Standard institutional template for statutory bail.",
            "content_template": "IN THE COURT OF SESSIONS... Accused: {{accused_name}}",
            "required_fields": ["accused_name", "custody_duration_days"],
            "required_documents": ["charge_sheet"],
        },
    )
    assert res_create.status_code == 201
    tmpl_data = res_create.json()
    tmpl_id = tmpl_data["id"]
    assert tmpl_data["version"] == 1
    assert tmpl_data["organization_id"] == "org_slsa_delhi"

    # Update template to create Version 2
    res_update = client.put(
        f"/api/documents/templates/{tmpl_id}",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={
            "description": "Updated statutory grounds template.",
            "content_template": "REVISED IN THE COURT OF SESSIONS... Accused: {{accused_name}}",
        },
    )
    assert res_update.status_code == 200
    updated_data = res_update.json()
    assert updated_data["version"] == 2
    assert "REVISED" in updated_data["content_template"]


def test_gov_admin_cannot_create_template_for_external_org(gov_token):
    """Gov Admin cannot create templates on behalf of an external organization (403 Forbidden)."""
    res = client.post(
        "/api/documents/templates",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={
            "name": "Unauthorized Template Creation",
            "doc_type": "BAIL_APPLICATION",
            "jurisdiction": "National / BNSS 2023",
            "statutory_ground": "Section 479 BNSS 2023",
            "content_template": "Pleading text",
            "organization_id": "org_slsa_karnataka",
        },
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")


# ── 5. Institutional Capability Delegations ───────────────────────────────────

def test_gov_admin_can_grant_and_revoke_delegation(gov_token):
    """Gov Admin can grant time-bound institutional capability delegation and revoke it."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    future_iso = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).isoformat()

    res_grant = client.post(
        "/api/documents/delegations",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={
            "granted_to_user_id": "dlsa_officer_delhi_01",
            "granted_to_role": "DLSA_OFFICER",
            "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
            "allowed_document_types": ["BAIL_APPLICATION"],
            "allowed_case_scope": ["*"],
            "valid_from": now_iso,
            "valid_until": future_iso,
            "reason": "SLSA Special Undertrial Review Mission 2026 - authorized Section 479 drafting mandate",
        },
    )
    assert res_grant.status_code == 201
    delg_data = res_grant.json()
    delg_id = delg_data["delegation_id"]
    assert delg_data["status"] == "ACTIVE"
    assert delg_data["granted_by_role"] == Role.GOV_ADMIN.value

    # Revoke delegation
    res_revoke = client.post(
        f"/api/documents/delegations/{delg_id}/revoke",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={"reason": "Special drive completed."},
    )
    assert res_revoke.status_code == 200
    revoke_data = res_revoke.json()
    assert revoke_data["status"] == "REVOKED"


def test_gov_admin_cannot_grant_or_revoke_cross_org_delegation(gov_token):
    """Gov Admin cannot grant or revoke delegations for external organizations (403 Forbidden)."""
    future_iso = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).isoformat()

    # Attempt cross-organization grant
    res_grant = client.post(
        "/api/documents/delegations",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={
            "granted_to_user_id": "dlsa_officer_mumbai_01",
            "granted_to_role": "DLSA_OFFICER",
            "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
            "valid_until": future_iso,
            "reason": "Cross-org unauthorized grant attempt",
            "organization_id": "org_slsa_maharashtra",
        },
    )
    assert res_grant.status_code == 403

    # Seed foreign delegation
    foreign_delg_id = f"delg_foreign_{uuid.uuid4().hex[:6]}"
    store_institutional_delegation({
        "delegation_id": foreign_delg_id,
        "granted_to_user_id": "dlsa_mumbai_officer",
        "granted_to_role": "DLSA_OFFICER",
        "granted_by_user_id": "slsa_maharashtra_admin",
        "granted_by_role": "GOV_ADMIN",
        "organization_id": "org_slsa_maharashtra",
        "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
        "allowed_document_types": ["*"],
        "allowed_case_scope": ["*"],
        "valid_from": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "valid_until": future_iso,
        "status": "ACTIVE",
        "reason": "Maharashtra internal delegation",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    # Attempt cross-organization revoke
    res_revoke = client.post(
        f"/api/documents/delegations/{foreign_delg_id}/revoke",
        headers={"Authorization": f"Bearer {gov_token}"},
        json={"reason": "Unauthorized cross-org revocation attempt"},
    )
    assert res_revoke.status_code == 403
    assert "Forbidden" in res_revoke.json().get("detail", "")


# ── 6. Zero Emojis Policy Compliance ─────────────────────────────────────────

def test_zero_emojis_in_gov_admin_routes_and_responses(gov_token):
    """Verify strictly zero emojis in Gov Admin responses across all endpoints."""
    emoji_pattern = re.compile(
        "[𐀀-􏿿😀-🙏🌀-🗿🚀-🛿🜀-🝿🞀-🟿🠀-🣿🤀-🧿🨀-🩯🩰-🫿☀-⛿✀-➿]",
        flags=re.UNICODE,
    )

    endpoints = [
        "/gov/overview",
        "/gov/districts",
        "/gov/sla",
        "/gov/exceptions",
        "/api/documents/templates",
        "/api/documents/delegations",
    ]

    for ep in endpoints:
        res = client.get(ep, headers={"Authorization": f"Bearer {gov_token}"})
        assert res.status_code in (200, 201), f"Endpoint {ep} failed with {res.status_code}"
        text_content = res.text
        assert not emoji_pattern.search(text_content), f"Emoji found in response for {ep}: {text_content}"

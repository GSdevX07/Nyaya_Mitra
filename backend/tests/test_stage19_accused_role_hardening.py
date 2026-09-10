"""
test_stage19_accused_role_hardening.py
======================================
Comprehensive Stage 19 Role Hardening Verification for ACCUSED_USER and FAMILY_GUARDIAN.
Tests citizen-facing access strictly bounded to linked own case, plain-language legal aid status,
entitled approved documents and summaries, request workflows, notification preferences, consent,
strict 403/404 denial of internal drafts, legal strategy, reviewer notes, AI internal metadata,
internal audit logs, protected evidence, and document ID guessing. Strictly zero emojis.
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
    store_uploaded_document,
    store_document_version,
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
        "present_docs": ["fir", "remand_order", "charge_sheet", "custody_certificate"],
        "urgency_flags": {"age": 32, "health_flag": False, "repeat_offender": False},
        "jail_location": "Tihar Central Jail No. 4",
        "district": "Central Delhi",
        "state": "Delhi",
        "court_name": "Central District Court, Tis Hazari",
        "police_station": "Kotwali",
        "fir_number": "FIR-2024-0101",
        "parent_name": "Harbans Singh",
        "relative_name": "Harbans Singh",
        "relative_relation": "Father",
        "relative_phone": "+91 98765 43210",
        "permanent_address": "House 12, Ward 4, Kotwali, Central Delhi",
        "assignment_status": "ASSIGNED",
        "assigned_lawyer_id": "demo_advocate",
        "assigned_lawyer": "Adv. Rajesh Sharma",
        "data_source_status": "DEMO_SYNTHETIC",
        "status": "SUBMITTED",
        "evidence_verified": True,
        "organization_id": "org_dlsa_central",
    }
    full_dict = {**defaults, **case_dict}
    case_rec = CaseRecord(**full_dict)
    _MEMORY_CASES[case_rec.case_id] = case_rec

    from app.supabase_adapter import is_supabase_active, get_supabase_client
    if is_supabase_active():
        try:
            supa = get_supabase_client()
            if supa:
                supa.table("cases").upsert({
                    "case_id": case_rec.case_id,
                    "data": case_rec.model_dump_json(),
                    "status": case_rec.status.value if hasattr(case_rec.status, "value") else str(case_rec.status),
                    "assignment_status": case_rec.assignment_status,
                    "assigned_lawyer_id": case_rec.assigned_lawyer_id,
                }).execute()
        except Exception:
            pass

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
def accused_token():
    """Accused Person Token explicitly linked to UTP-0001."""
    claims = {
        "email": "suresh.patel@citizen.in",
        "full_name": "Suresh Patel",
        "linked_case_id": "UTP-0001",
        "phone_number": "+91 98765 43210",
        "district": "Central Delhi",
        "state": "Delhi",
    }
    return create_access_token(
        subject="demo_accused",
        role=Role.ACCUSED_USER.value,
        org_id="org_dlsa_central",
        extra_claims=claims,
    )


@pytest.fixture
def family_token():
    """Family Guardian Token explicitly linked to UTP-0001."""
    claims = {
        "email": "harbans.singh@citizen.in",
        "full_name": "Harbans Singh",
        "linked_case_id": "UTP-0001",
        "relationship": "Father",
        "phone_number": "+91 98765 43210",
        "district": "Central Delhi",
        "state": "Delhi",
    }
    return create_access_token(
        subject="demo_family",
        role=Role.FAMILY_GUARDIAN.value,
        org_id="org_dlsa_central",
        extra_claims=claims,
    )


@pytest.fixture
def unlinked_accused_token():
    """Accused Person Token with NO linked case."""
    claims = {
        "email": "unlinked.citizen@citizen.in",
        "full_name": "Unlinked Citizen",
        "phone_number": "+91 98765 00000",
        "district": "Central Delhi",
        "state": "Delhi",
    }
    return create_access_token(
        subject="unlinked_accused",
        role=Role.ACCUSED_USER.value,
        org_id="org_dlsa_central",
        extra_claims=claims,
    )


# ==============================================================================
# 1. ALLOWED: Citizen-Facing Own Case Status & Plain-Language Views
# ==============================================================================

def test_accused_can_view_own_case_overview(accused_token):
    """Accused person can access consolidated, plain-language overview for own linked case."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    resp = client.get(
        "/citizen/overview",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["portal_mode"] == "ACCUSED_USER"
    assert data["case_reference"] == "UTP-0001"
    assert "legal_aid_support" in data
    assert "upcoming_known_events" in data
    assert "approved_entitled_documents" in data
    assert "ai_procedural_explanation" in data
    assert data["support_helpline"] == "15100"


def test_accused_can_view_own_case_my_case(accused_token):
    """Accused person can access /citizen/my-case for simplified plain-language status."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    resp = client.get(
        "/citizen/my-case",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("case_id") == "UTP-0001" or data.get("case_reference") == "UTP-0001"


def test_accused_can_view_own_case_dossier(accused_token):
    """Accused person can access GET /cases/UTP-0001, receiving sanitized projection with zero internal drafts/strategy."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    resp = client.get(
        "/cases/UTP-0001",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("citizen_authorized_view") is True
    assert data.get("draft") is None
    assert data.get("legal_strategy_notes") is None
    assert data.get("internal_strategy_notes") is None
    assert data.get("supervisory_review_notes") is None
    assert data.get("statutes") is None
    assert data.get("retrieval") is None
    assert data.get("agent_activity_log") == []
    assert "case" in data


def test_accused_cannot_view_another_case_dossier(accused_token):
    """Accused person is strictly forbidden from accessing another case even if knowing the case ID."""
    _insert_test_case({"case_id": "UTP-0002", "name": "Another Prisoner"})
    resp = client.get(
        "/cases/UTP-0002",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]


def test_unlinked_accused_cannot_view_case_dossier(unlinked_accused_token):
    """Accused user with no linked case cannot access any case dossier."""
    resp = client.get(
        "/cases/UTP-0001",
        headers={"Authorization": f"Bearer {unlinked_accused_token}"},
    )
    assert resp.status_code == 403


def test_accused_cannot_enumerate_master_cases_roster(accused_token):
    """Accused user cannot access the master cases roster (GET /cases)."""
    resp = client.get(
        "/cases",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


def test_accused_cannot_view_available_cases(accused_token):
    """Accused user cannot access available cases allocation roster."""
    resp = client.get(
        "/cases/available",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


# ==============================================================================
# 2. ALLOWED: Safe Chronological Milestone Timelines & Profiles
# ==============================================================================

def test_accused_can_view_own_citizen_timeline(accused_token):
    """Accused user can view citizen milestone timeline, strictly sanitized of audit events."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    resp = client.get(
        "/citizen/timeline",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)
    for ev in events:
        assert not ev.get("title", "").startswith("Audit:")
        assert ev.get("category") != "EVIDENCE_INTEGRITY"
        assert ev.get("category") != "SECURITY_ALERT"


def test_accused_can_view_own_accused_timeline(accused_token):
    """Accused user can view own timeline via /accused/{accused_id}/timeline."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    resp = client.get(
        "/accused/acc_utp_0001/timeline",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)
    for ev in events:
        assert not ev.get("title", "").startswith("Audit:")


def test_accused_cannot_view_another_accused_timeline(accused_token):
    """Accused user cannot view another individual's timeline."""
    _insert_test_case({"case_id": "UTP-0002", "name": "Other Person"})
    resp = client.get(
        "/accused/acc_utp_0002/timeline",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


def test_accused_can_view_own_accused_profile(accused_token):
    """Accused user can view own profile with PII/medical view separation."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    resp = client.get(
        "/accused/acc_utp_0001",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("is_accused_self_view") is True
    assert data.get("government_identifiers") == {}
    med = data.get("medical_record")
    if med:
        assert med.get("is_redacted") is True or "RESTRICTED" in str(med.get("details_restricted", ""))


def test_accused_cannot_view_another_accused_profile(accused_token):
    """Accused user cannot view another accused person's profile."""
    _insert_test_case({"case_id": "UTP-0002", "name": "Other Person"})
    resp = client.get(
        "/accused/acc_utp_0002",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


def test_accused_can_view_own_connected_cases(accused_token):
    """Accused user can list connected court cases for own profile."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    resp = client.get(
        "/accused/acc_utp_0001/cases",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    cases = resp.json()
    assert isinstance(cases, list)


def test_accused_cannot_view_another_connected_cases(accused_token):
    """Accused user cannot list connected cases for another person."""
    resp = client.get(
        "/accused/acc_utp_0002/cases",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


# ==============================================================================
# 3. ALLOWED: Entitled Documents & Low-Bandwidth Text Summaries
# ==============================================================================

def test_accused_can_list_entitled_documents(accused_token):
    """Accused user can list approved documents entitled to citizen/family."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    resp = client.get(
        "/citizen/documents",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    docs = resp.json()
    assert isinstance(docs, list)
    for d in docs:
        assert d.get("is_approved_for_citizen") is True


def test_accused_can_view_entitled_document_summary(accused_token):
    """Accused user can view low-bandwidth plain-text summary of entitled document."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel", "present_docs": ["fir", "remand_order", "charge_sheet"]})
    resp = client.get(
        "/citizen/documents/doc_UTP-0001_fir/summary",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "UTP-0001"
    assert "text_summary" in data


def test_accused_cannot_guess_unrecorded_document_id(accused_token):
    """Guessing arbitrary document IDs returns 404 Not Found."""
    resp = client.get(
        "/citizen/documents/doc_random_fictitious_id_99999/summary",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 404


def test_accused_cannot_access_privileged_document_summary(accused_token):
    """Accessing an unapproved or privileged document type is strictly denied with 403."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO uploaded_documents (id, case_id, document_type, file_name, extracted_text, file_hash, file_size_bytes, uploaded_by, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "doc_priv_strategy_001",
            "UTP-0001",
            "internal_legal_strategy_memo",
            "strategy.pdf",
            "Privileged defense counsel strategy notes",
            "hash123",
            1024,
            "demo_advocate",
            "2026-09-10T10:00:00Z",
        ),
    )
    conn.commit()
    conn.close()

    resp = client.get(
        "/citizen/documents/doc_priv_strategy_001/summary",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403
    assert "not authorized for release to citizen" in resp.json()["detail"].lower()


# ==============================================================================
# 4. ALLOWED: Citizen Action Requests, Notification Preferences & Consent
# ==============================================================================

def test_accused_can_submit_help_request(accused_token):
    """Accused user can submit structured Citizen Help Request."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    payload = {
        "request_type": "REQUEST_HELP",
        "subject": "Need assistance with court production date",
        "details": "Please inform when next hearing date is scheduled.",
    }
    resp = client.post(
        "/citizen/requests",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUBMITTED"
    assert "id" in data


def test_accused_can_submit_copy_request(accused_token):
    """Accused user can submit copy request for charge sheet."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    payload = {
        "request_type": "REQUEST_DOCUMENT_COPY",
        "subject": "Copy of Charge Sheet required",
        "details": "Requesting certified copy of police charge sheet for family review.",
        "target_document_type": "charge_sheet",
    }
    resp = client.post(
        "/citizen/requests",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 200


def test_accused_can_report_incorrect_info(accused_token):
    """Accused user can flag discrepancy in case data."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    payload = {
        "request_type": "FLAG_INCORRECT_INFO",
        "subject": "Custody arrest date discrepancy",
        "details": "Actual arrest date was 2 days prior to recorded date.",
        "discrepancy_field": "arrest_date",
    }
    resp = client.post(
        "/citizen/requests",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 200


def test_accused_can_list_submitted_requests(accused_token):
    """Accused user can view historical submitted citizen requests."""
    resp = client.get(
        "/citizen/requests",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_accused_can_view_and_update_notification_preferences(accused_token):
    """Accused user can view and update multi-channel notification preferences."""
    resp = client.get(
        "/citizen/notification-preferences",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200

    update_payload = {
        "phone_number": "+91 98765 43210",
        "channel_sms_enabled": True,
        "channel_whatsapp_enabled": True,
        "channel_in_app_enabled": True,
        "preferred_language": "hi",
        "consent_status": "OPTED_IN",
    }
    resp2 = client.post(
        "/citizen/notification-preferences",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=update_payload,
    )
    assert resp2.status_code == 200


def test_accused_can_view_privacy_notice(accused_token):
    """Accused user can fetch multilingual statutory privacy notice."""
    resp = client.get("/citizen/privacy-notice?lang=hi")
    assert resp.status_code == 200
    data = resp.json()
    assert "purpose" in data or "privacy_notice" in data or "sections" in data or "title" in data


def test_accused_can_manage_privacy_consent(accused_token):
    """Accused user can grant, check, and revoke statutory consent."""
    # Check status
    resp = client.get(
        "/citizen/consent/status",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200

    # Grant consent
    resp2 = client.post(
        "/citizen/consent",
        headers={"Authorization": f"Bearer {accused_token}"},
        json={"consent_type": "DATA_PROCESSING", "version": "2026.1"},
    )
    assert resp2.status_code == 200

    # Revoke consent
    resp3 = client.post(
        "/citizen/consent/revoke",
        headers={"Authorization": f"Bearer {accused_token}"},
        json={"consent_type": "DATA_PROCESSING", "reason": "Citizen requested revocation"},
    )
    assert resp3.status_code == 200


def test_accused_can_list_supported_languages(accused_token):
    """Accused user can list supported regional languages."""
    resp = client.get(
        "/citizen/languages",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 7


# ==============================================================================
# 5. FAMILY_GUARDIAN: Linked Scope and Address Redaction
# ==============================================================================

def test_family_guardian_can_view_linked_case_overview(family_token):
    """Family guardian can access citizen overview for linked accused."""
    _insert_test_case({"case_id": "UTP-0001", "name": "Suresh Patel"})
    resp = client.get(
        "/citizen/overview",
        headers={"Authorization": f"Bearer {family_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["portal_mode"] == "FAMILY_GUARDIAN"
    assert data["case_reference"] == "UTP-0001"


def test_family_guardian_cannot_view_another_case(family_token):
    """Family guardian cannot access another unlinked case."""
    resp = client.get(
        "/cases/UTP-0002",
        headers={"Authorization": f"Bearer {family_token}"},
    )
    assert resp.status_code == 403


# ==============================================================================
# 6. STRICT 403 FORBIDDEN: Denied Workspaces, Drafting & Judicial Mutations
# ==============================================================================

def test_accused_cannot_access_internal_drafts_by_case(accused_token):
    """ACCUSED_USER cannot access internal document workspace drafts."""
    resp = client.get(
        "/api/documents/drafts/case/UTP-0001",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


def test_accused_cannot_access_internal_draft_by_id(accused_token):
    """ACCUSED_USER cannot access specific draft by ID."""
    resp = client.get(
        "/api/documents/drafts/draft_001",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


def test_accused_cannot_generate_draft(accused_token):
    """ACCUSED_USER cannot generate internal document drafts."""
    payload = {
        "case_id": "UTP-0001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "custom_instructions": "Draft bail application",
    }
    resp = client.post(
        "/api/documents/drafts/generate",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 403


def test_accused_cannot_edit_draft(accused_token):
    """ACCUSED_USER cannot edit legal pleadings."""
    payload = {"content_text": "Modified text"}
    resp = client.put(
        "/api/documents/drafts/draft_001",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 403


def test_accused_cannot_comment_on_draft(accused_token):
    """ACCUSED_USER cannot add internal comments to drafts."""
    payload = {"comment": "My comment on legal draft"}
    resp = client.post(
        "/api/documents/drafts/draft_001/comments",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 403


def test_accused_cannot_approve_or_reject_draft(accused_token):
    """ACCUSED_USER cannot approve or reject legal drafts."""
    resp1 = client.post(
        "/api/documents/drafts/draft_001/approve",
        headers={"Authorization": f"Bearer {accused_token}"},
        json={"comment": "Approved"},
    )
    assert resp1.status_code == 403

    resp2 = client.post(
        "/api/documents/drafts/draft_001/reject",
        headers={"Authorization": f"Bearer {accused_token}"},
        json={"reason": "Rejected"},
    )
    assert resp2.status_code == 403


def test_accused_cannot_request_revisions_on_draft(accused_token):
    """ACCUSED_USER cannot issue supervisory revision requests."""
    payload = {"reason": "Revise pleading paragraphs", "instructions": "More details"}
    resp = client.post(
        "/api/documents/drafts/draft_001/request-revisions",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 403


def test_accused_cannot_package_draft(accused_token):
    """ACCUSED_USER cannot package court submission bundles."""
    payload = {"exhibits": ["exhibit_1"]}
    resp = client.post(
        "/api/documents/drafts/draft_001/package",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 403


def test_accused_cannot_record_filing(accused_token):
    """ACCUSED_USER cannot record court filings."""
    payload = {"filing_reference": "FIL-2026-001"}
    resp = client.post(
        "/api/documents/drafts/draft_001/record-filing",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 403


def test_accused_cannot_create_or_update_template(accused_token):
    """ACCUSED_USER cannot administer document templates."""
    resp1 = client.post(
        "/api/documents/templates",
        headers={"Authorization": f"Bearer {accused_token}"},
        json={
            "name": "Custom Bail Template",
            "doc_type": "BAIL_APPLICATION",
            "statutory_ground": "Section 479 BNSS",
            "content_template": "IN THE COURT OF...",
        },
    )
    assert resp1.status_code == 403

    resp2 = client.put(
        "/api/documents/templates/tmpl_bnss_479_bail_v1",
        headers={"Authorization": f"Bearer {accused_token}"},
        json={"name": "Updated Template"},
    )
    assert resp2.status_code == 403


def test_accused_cannot_grant_or_revoke_delegation(accused_token):
    """ACCUSED_USER cannot grant or revoke institutional delegations."""
    payload = {
        "granted_to_user_id": "adv_001",
        "granted_to_role": "DEFENSE_ADVOCATE",
        "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
        "valid_until": "2026-12-31T23:59:59Z",
        "reason": "Test delegation",
    }
    resp = client.post(
        "/api/documents/delegations",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 403


def test_accused_cannot_approve_case(accused_token):
    """ACCUSED_USER cannot execute consequential case approvals."""
    resp = client.post(
        "/cases/UTP-0001/approve",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


def test_accused_cannot_file_case(accused_token):
    """ACCUSED_USER cannot file cases in court."""
    resp = client.post(
        "/cases/UTP-0001/file",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


def test_accused_cannot_assign_counsel(accused_token):
    """ACCUSED_USER cannot assign defense counsel."""
    payload = {"lawyer_id": "adv_001", "lawyer_name": "Adv. Sharma"}
    resp = client.post(
        "/cases/UTP-0001/assign-counsel",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 403


def test_accused_cannot_take_or_decline_case(accused_token):
    """ACCUSED_USER cannot take up or decline cases."""
    resp1 = client.post(
        "/cases/UTP-0001/take",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp1.status_code == 403

    resp2 = client.post(
        "/cases/UTP-0001/decline",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp2.status_code == 403


def test_accused_cannot_upload_official_documents(accused_token):
    """ACCUSED_USER cannot upload official court/jail records via /documents/upload."""
    resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=remand_order",
        headers={"Authorization": f"Bearer {accused_token}"},
        data={"custom_text": "Sample text"},
    )
    assert resp.status_code == 403


def test_accused_cannot_download_raw_documents(accused_token):
    """ACCUSED_USER cannot download raw files via /documents/download/{id}."""
    resp = client.get(
        "/documents/download/doc_001",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


def test_accused_cannot_access_evidence_chain(accused_token):
    """ACCUSED_USER cannot access raw evidence chains."""
    resp = client.get(
        "/documents/doc_001/evidence-chain",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp.status_code == 403


def test_accused_cannot_access_audit_ledger(accused_token):
    """ACCUSED_USER cannot access audit events or verify integrity."""
    resp1 = client.get(
        "/audit-events",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp1.status_code == 403

    resp2 = client.get(
        "/audit/verify-integrity",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp2.status_code == 403


def test_accused_cannot_trigger_actions_or_clear_notifications(accused_token):
    """ACCUSED_USER cannot trigger actions or clear notifications."""
    resp1 = client.post(
        "/actions/trigger",
        headers={"Authorization": f"Bearer {accused_token}"},
        json={"action_id": "act_001"},
    )
    assert resp1.status_code == 403

    resp2 = client.post(
        "/notifications/clear",
        headers={"Authorization": f"Bearer {accused_token}"},
        json={"notification_ids": ["notif_001"]},
    )
    assert resp2.status_code == 403


def test_accused_cannot_modify_rules_or_schedules(accused_token):
    """ACCUSED_USER cannot modify deterministic rules or scheduled analytics."""
    resp1 = client.post(
        "/rules/rule_001/lifecycle",
        headers={"Authorization": f"Bearer {accused_token}"},
        json={"target_state": "RETIRED", "notes": "Test transition"},
    )
    assert resp1.status_code == 403

    resp2 = client.post(
        "/api/analytics/schedules/sch_001/trigger",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp2.status_code == 403


def test_accused_cannot_update_identity_attributes(accused_token):
    """ACCUSED_USER cannot mutate consolidated legal identity records."""
    payload = {"full_name": "New Name", "update_reason": "Correction of name"}
    resp = client.patch(
        "/accused/acc_utp_0001/identity",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 403


def test_accused_cannot_resolve_duplicates(accused_token):
    """ACCUSED_USER cannot execute duplicate resolution workflows."""
    payload = {
        "candidate_id": "cand_001",
        "action": "MERGE_RECORDS",
        "resolution_notes": "Merge duplicate records",
    }
    resp = client.post(
        "/accused/duplicates/resolve",
        headers={"Authorization": f"Bearer {accused_token}"},
        json=payload,
    )
    assert resp.status_code == 403


# ==============================================================================
# 7. ZERO EMOJI COMPLIANCE
# ==============================================================================

def test_zero_emojis_in_accused_routes_and_responses(accused_token):
    """Ensure strictly zero emojis in citizen overview, my-case, timeline, and document summaries."""
    emoji_regex = re.compile(r"[𐀀-􏿿☀-⛿✀-➿]")

    # 1. Overview
    resp1 = client.get(
        "/citizen/overview",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp1.status_code == 200
    assert not emoji_regex.search(resp1.text)

    # 2. My case
    resp2 = client.get(
        "/citizen/my-case",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp2.status_code == 200
    assert not emoji_regex.search(resp2.text)

    # 3. Timeline
    resp3 = client.get(
        "/citizen/timeline",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp3.status_code == 200
    assert not emoji_regex.search(resp3.text)

    # 4. Documents
    resp4 = client.get(
        "/citizen/documents",
        headers={"Authorization": f"Bearer {accused_token}"},
    )
    assert resp4.status_code == 200
    assert not emoji_regex.search(resp4.text)

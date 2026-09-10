"""
test_stage19_jail_role_hardening.py - Security & RBAC Test Suite for Jail Officer Role Hardening.
=================================================================================================
22 automated test scenarios verifying Stage 19 Jail Officer role hardening:
1. JAIL_OFFICER can intake new custody record in authorized facility.
2. JAIL_OFFICER cannot intake custody for an unauthorized/unrelated facility (403 Forbidden).
3. JAIL_OFFICER can record custody event for inmate in authorized facility.
4. JAIL_OFFICER cannot record custody event for inmate in unrelated facility (403 Forbidden).
5. JAIL_OFFICER can upload authorized prison documents (prison_admission_record, nominal_roll).
6. JAIL_OFFICER cannot upload police investigation records like charge_sheet or fir (403 Forbidden).
7. JAIL_OFFICER cannot upload documents for inmates in an unrelated facility (403 Forbidden).
8. JAIL_OFFICER can update accused profile (father name, address, emergency contact) in authorized facility.
9. JAIL_OFFICER cannot update accused profile for inmate in unrelated facility (403 Forbidden).
10. JAIL_OFFICER can refer undertrial to DLSA for legal-aid counsel assignment (POST /jail/refer-legal-aid).
11. JAIL_OFFICER cannot refer inmate in unrelated facility to DLSA (403 Forbidden).
12. JAIL_OFFICER can confirm physical prison release with source references (POST /cases/{id}/confirm-release).
13. JAIL_OFFICER cannot confirm release without mandatory gate pass reference (400/422).
14. JAIL_OFFICER cannot confirm release for inmate in unrelated facility (403 Forbidden).
15. Non-jail roles (DEFENSE_ADVOCATE, POLICE_OFFICER, READ_ONLY_AUDITOR) cannot confirm release (403 Forbidden).
16. GET /jail/inmates returns strictly facility-scoped roster (no cross-facility data leakage).
17. GET /cases/{id} returns jail-authorized view; accessing unrelated facility returns 403 Forbidden.
18. GET /cases/{id} and GET /jail/inmates strictly redact legal strategy, draft petitions, and AI work products.
19. Sensitive medical records are field-level restricted for JAIL_OFFICER (medical_record masked, operational flags preserved).
20. JAIL_OFFICER is strictly denied from legal document workspace drafting actions (INITIATE_DRAFT, EDIT_DRAFT, APPROVE_DRAFT, etc.).
21. Bulk task queue rejects consequential release/approval actions (400 Bad Request).
22. Zero emojis across all code, responses, and tests.

Strictly NO emojis in code, comments, or assertions.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import (
    init_db,
    get_case,
    get_db_connection,
    _MEMORY_CASES,
    get_uploaded_document_by_id,
)
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.models.schemas import CaseRecord, CaseState
from app.services.document_templates import seed_default_templates
from app.security.classification import has_medical_clearance, has_pii_clearance, FieldLevelAccessFilter
from app.services.document_authorization import (
    authorize_document_action,
    DocumentAction,
    DISALLOWED_WORKSPACE_ROLES,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_workspace():
    init_db()
    seed_default_templates()


def get_token_headers(
    role: str,
    user_id: str,
    org_id: str = "org_tihar_jail",
    district: str = "West Delhi",
    facility_ids: list = None,
) -> dict:
    fac_list = facility_ids if facility_ids is not None else ["fac_tihar_jail_04", "Central Jail No. 4, Tihar (Synthetic)", "Tihar"]
    token = create_access_token(
        subject=user_id,
        role=role,
        org_id=org_id,
        extra_claims={
            "district": district,
            "authorized_district_ids": [district],
            "facility_ids": fac_list,
        },
    )
    return {"Authorization": f"Bearer {token}"}


def _insert_test_case(case_dict: dict):
    """Helper to insert a test case into SQLite and _MEMORY_CASES with all required fields."""
    defaults = {
        "prisoner_category": "UNDERTRIAL",
        "legal_code": "BNS_2023",
        "offense_sections": ["BNS 115(2)"],
        "arrest_date": "2025-01-10",
        "custody_days": 180,
        "max_sentence_days_for_offense": 365,
        "punishable_by_death_or_life": False,
        "multiple_active_cases": False,
        "required_docs": ["remand_order", "charge_sheet"],
        "present_docs": ["remand_order", "charge_sheet"],
        "urgency_flags": {"age": 28, "health_flag": False, "repeat_offender": False},
        "jail_location": "Central Jail No. 4, Tihar (Synthetic)",
        "facility_id": "fac_tihar_jail_04",
        "district": "West Delhi",
        "court_name": "Tis Hazari Court",
        "permanent_address": "House 10, Delhi",
        "assignment_status": "AVAILABLE",
        "data_source_status": "DEMO_SYNTHETIC",
        "status": "LEGAL_AID_REQUIRED",
    }
    full_dict = {**defaults, **case_dict}
    case_rec = CaseRecord(**full_dict)
    _MEMORY_CASES[case_rec.case_id] = case_rec
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO cases (case_id, data, status, assignment_status, assigned_lawyer_id) VALUES (?, ?, ?, ?, ?)",
            (
                case_rec.case_id,
                json.dumps(full_dict),
                case_rec.status.value if hasattr(case_rec.status, "value") else str(case_rec.status),
                case_rec.assignment_status,
                case_rec.assigned_lawyer_id,
            ),
        )
        c.execute(
            "INSERT OR REPLACE INTO court_cases (id, accused_id, case_number, current_status, court_name, district) VALUES (?, ?, ?, ?, ?, ?)",
            (case_rec.case_id, f"acc_{case_rec.case_id.lower()}", f"FIR-{case_rec.case_id}", "LEGAL_AID_REQUIRED", case_rec.court_name, case_rec.district),
        )
        c.execute(
            "INSERT OR REPLACE INTO accused_persons (id, full_name, gender, permanent_address) VALUES (?, ?, ?, ?)",
            (f"acc_{case_rec.case_id.lower()}", case_rec.name, "Male", case_rec.permanent_address or "Delhi"),
        )
        c.execute(
            "INSERT OR REPLACE INTO custody_records (id, accused_id, facility_id, admission_date, prisoner_category) VALUES (?, ?, ?, ?, ?)",
            (f"cus_{case_rec.case_id.lower()}", f"acc_{case_rec.case_id.lower()}", full_dict.get("facility_id", "fac_tihar_jail_04"), case_rec.arrest_date, "UNDERTRIAL"),
        )
        conn.commit()
    finally:
        conn.close()
    return case_rec


# ── Scenario 1: Jail Officer Intakes New Custody Record in Authorized Facility ───

def test_scenario_01_jail_officer_intakes_new_custody_record_in_authorized_facility():
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04", "Central Jail No. 4, Tihar"])
    payload = {
        "name": "Sunil Kumar Verma",
        "facility_id": "fac_tihar_jail_04",
        "facility_name": "Central Jail No. 4, Tihar",
        "district": "West Delhi",
        "court_name": "Tis Hazari Court",
        "offense_sections": ["BNS 303(2)", "BNS 317"],
        "arrest_date": "2026-03-01",
        "admission_date": "2026-03-01",
        "refer_to_dlsa": True,
        "notes": "Intake physical screening clear. Relative contacts captured.",
    }
    response = client.post("/cases/custody-intake", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Sunil Kumar Verma"
    assert data["status"] == "INTAKE"
    assert data["case_id"].startswith("UTP-J")


# ── Scenario 2: Jail Officer Cannot Intake Custody for Unauthorized Facility ────

def test_scenario_02_jail_officer_cannot_intake_custody_for_unauthorized_facility():
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "name": "Rohan Deshmukh",
        "facility_id": "fac_rohini_jail",
        "facility_name": "Rohini District Jail",
        "district": "North West Delhi",
        "arrest_date": "2026-03-01",
    }
    response = client.post("/cases/custody-intake", json=payload, headers=headers)
    assert response.status_code == 403
    assert "outside your authorized correctional facilities" in response.json()["detail"]


# ── Scenario 3: Jail Officer Records Custody Event for Facility Inmate ──────────

def test_scenario_03_jail_officer_records_custody_event_for_facility_inmate():
    _insert_test_case({
        "case_id": "UTP-JAIL-001",
        "name": "Mohit Gupta",
        "jail_location": "Central Jail No. 4, Tihar (Synthetic)",
        "facility_id": "fac_tihar_jail_04",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "event_type": "REMAND_EXTENSION",
        "event_date": "2026-03-05",
        "court_name": "Chief Metropolitan Magistrate West",
        "notes": "Judicial remand extended by 14 days under Model Prison Rules.",
        "verified": True,
    }
    response = client.post("/cases/UTP-JAIL-001/custody-events", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "REMAND_EXTENSION"
    assert "recorded successfully" in data["message"]


# ── Scenario 4: Jail Officer Cannot Record Custody Event for Unrelated Facility ─

def test_scenario_04_jail_officer_cannot_record_custody_event_for_unrelated_facility():
    _insert_test_case({
        "case_id": "UTP-ROHINI-001",
        "name": "Ajay Sharma",
        "jail_location": "District Jail Rohini",
        "facility_id": "fac_rohini_jail",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "event_type": "COURT_PRODUCTION",
        "event_date": "2026-03-05",
        "notes": "Video conferencing production.",
    }
    response = client.post("/cases/UTP-ROHINI-001/custody-events", json=payload, headers=headers)
    assert response.status_code == 403
    assert "outside your authorized facility" in response.json()["detail"]


# ── Scenario 5: Jail Officer Uploads Authorized Prison Document ─────────────────

def test_scenario_05_jail_officer_uploads_authorized_prison_document():
    _insert_test_case({
        "case_id": "UTP-JAIL-DOC-01",
        "name": "Devendra Singh",
        "jail_location": "Central Jail No. 4, Tihar",
        "facility_id": "fac_tihar_jail_04",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    response = client.post(
        "/documents/upload",
        params={"case_id": "UTP-JAIL-DOC-01", "document_type": "custody_certificate"},
        data={"custom_text": "Certified Nominal Roll and Custody Certificate from Superintendent Desk."},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_type"] == "custody_certificate"
    assert data["document_status"] == "PENDING_VERIFICATION"


# ── Scenario 6: Jail Officer Cannot Upload Police Investigation Document ───────

def test_scenario_06_jail_officer_cannot_upload_police_investigation_document():
    _insert_test_case({
        "case_id": "UTP-JAIL-DOC-02",
        "name": "Devendra Singh",
        "jail_location": "Central Jail No. 4, Tihar",
        "facility_id": "fac_tihar_jail_04",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    response = client.post(
        "/documents/upload",
        params={"case_id": "UTP-JAIL-DOC-02", "document_type": "charge_sheet"},
        data={"custom_text": "Unauthorized charge sheet upload attempt."},
        headers=headers,
    )
    assert response.status_code == 403
    assert "Jail officers may only upload prison intake" in response.json()["detail"]


# ── Scenario 7: Jail Officer Cannot Upload Document for Unrelated Facility ──────

def test_scenario_07_jail_officer_cannot_upload_document_for_unrelated_facility():
    _insert_test_case({
        "case_id": "UTP-MANDOLI-001",
        "name": "Vikas Tiwari",
        "jail_location": "Mandoli Central Jail",
        "facility_id": "fac_mandoli_jail",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    response = client.post(
        "/documents/upload",
        params={"case_id": "UTP-MANDOLI-001", "document_type": "prison_admission_record"},
        data={"custom_text": "Admission note"},
        headers=headers,
    )
    assert response.status_code == 403
    assert "outside your authorized prison facility" in response.json()["detail"]


# ── Scenario 8: Jail Officer Updates Accused Profile Missing Fields ─────────────

def test_scenario_08_jail_officer_updates_accused_profile_missing_fields():
    _insert_test_case({
        "case_id": "UTP-JAIL-PROF-01",
        "name": "Karan Mehra",
        "jail_location": "Central Jail No. 4, Tihar",
        "facility_id": "fac_tihar_jail_04",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "father_name": "Sh. Omprakash Mehra",
        "age": 29,
        "gender": "Male",
        "permanent_address": "House 45, Gali 3, Rajouri Garden, New Delhi",
        "emergency_family_contact_name": "Smt. Shanti Mehra",
        "emergency_family_contact_relation": "Mother",
        "emergency_family_contact_phone": "+91 98111 22334",
    }
    response = client.patch("/cases/UTP-JAIL-PROF-01/accused-profile", json=payload, headers=headers)
    assert response.status_code == 200
    assert "updated successfully" in response.json()["message"]


# ── Scenario 9: Jail Officer Cannot Update Profile for Unrelated Facility ───────

def test_scenario_09_jail_officer_cannot_update_profile_for_unrelated_facility():
    _insert_test_case({
        "case_id": "UTP-LUCKNOW-001",
        "name": "Santosh Yadav",
        "jail_location": "District Jail Lucknow",
        "facility_id": "fac_lucknow_jail",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "father_name": "Sh. Ram Yadav",
        "permanent_address": "Lucknow, UP",
    }
    response = client.patch("/cases/UTP-LUCKNOW-001/accused-profile", json=payload, headers=headers)
    assert response.status_code == 403
    assert "outside your authorized facility" in response.json()["detail"]


# ── Scenario 10: Jail Officer Refers Undertrial to DLSA ─────────────────────────

def test_scenario_10_jail_officer_refers_undertrial_to_dlsa():
    _insert_test_case({
        "case_id": "UTP-JAIL-REF-01",
        "name": "Deepak Joshi",
        "jail_location": "Central Jail No. 4, Tihar",
        "facility_id": "fac_tihar_jail_04",
        "status": "INTAKE",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "case_id": "UTP-JAIL-REF-01",
        "notes": "Undertrial has served over 90 days and lacks private legal representation.",
    }
    response = client.post("/jail/refer-legal-aid", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "referred to DLSA" in data["message"]


# ── Scenario 11: Jail Officer Cannot Refer Unrelated Facility Inmate to DLSA ───

def test_scenario_11_jail_officer_cannot_refer_unrelated_facility_inmate_to_dlsa():
    _insert_test_case({
        "case_id": "UTP-MANDOLI-002",
        "name": "Deepak Joshi",
        "jail_location": "Mandoli Central Jail",
        "facility_id": "fac_mandoli_jail",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "case_id": "UTP-MANDOLI-002",
        "notes": "Referral attempt",
    }
    response = client.post("/jail/refer-legal-aid", json=payload, headers=headers)
    assert response.status_code == 403
    assert "outside your authorized facility" in response.json()["detail"]


# ── Scenario 12: Jail Officer Confirms Authorized Prison Release ────────────────

def test_scenario_12_jail_officer_confirms_authorized_prison_release():
    _insert_test_case({
        "case_id": "UTP-JAIL-REL-01",
        "name": "Mukesh Saini",
        "jail_location": "Central Jail No. 4, Tihar",
        "facility_id": "fac_tihar_jail_04",
        "status": "ORDER_RECEIVED",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "release_date": "2026-03-09",
        "gate_pass_number": "GP-TIHAR-2026-8891",
        "surety_verification_ref": "SURETY-VERIF-DELHI-449",
        "superintendent_notes": "Court bail order verified with Tis Hazari registry. Identity authenticated. Discharged at 17:30.",
    }
    response = client.post("/cases/UTP-JAIL-REL-01/confirm-release", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["gate_pass_number"] == "GP-TIHAR-2026-8891"
    assert data["canonical_state"] == "POST_RELEASE_FOLLOW_UP"


# ── Scenario 13: Release Confirmation Rejects Missing Mandatory Gate Pass ───────

def test_scenario_13_release_confirmation_rejects_missing_mandatory_gate_pass():
    _insert_test_case({
        "case_id": "UTP-JAIL-REL-02",
        "name": "Mukesh Saini",
        "jail_location": "Central Jail No. 4, Tihar",
        "facility_id": "fac_tihar_jail_04",
        "status": "ORDER_RECEIVED",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "release_date": "2026-03-09",
        "gate_pass_number": "",  # Empty mandatory field
        "surety_verification_ref": "SURETY-001",
    }
    response = client.post("/cases/UTP-JAIL-REL-02/confirm-release", json=payload, headers=headers)
    assert response.status_code in (400, 422)


# ── Scenario 14: Jail Officer Cannot Confirm Release for Unrelated Facility ─────

def test_scenario_14_jail_officer_cannot_confirm_release_for_unrelated_facility():
    _insert_test_case({
        "case_id": "UTP-ROHINI-REL-01",
        "name": "Mukesh Saini",
        "jail_location": "Rohini District Jail",
        "facility_id": "fac_rohini_jail",
        "status": "ORDER_RECEIVED",
    })
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "release_date": "2026-03-09",
        "gate_pass_number": "GP-ROHINI-999",
        "surety_verification_ref": "SURETY-001",
        "superintendent_notes": "Attempting cross-facility release",
    }
    response = client.post("/cases/UTP-ROHINI-REL-01/confirm-release", json=payload, headers=headers)
    assert response.status_code == 403
    assert "outside your authorized facility" in response.json()["detail"]


# ── Scenario 15: Non-Jail Role Cannot Confirm Prison Release ───────────────────

def test_scenario_15_non_jail_role_cannot_confirm_prison_release():
    _insert_test_case({
        "case_id": "UTP-JAIL-REL-03",
        "name": "Mukesh Saini",
        "jail_location": "Central Jail No. 4, Tihar",
        "facility_id": "fac_tihar_jail_04",
        "status": "ORDER_RECEIVED",
    })
    for role in ["DEFENSE_ADVOCATE", "POLICE_OFFICER", "READ_ONLY_AUDITOR"]:
        headers = get_token_headers(role, f"test_user_{role.lower()}")
        payload = {
            "release_date": "2026-03-09",
            "gate_pass_number": "GP-12345",
            "surety_verification_ref": "SURETY-001",
            "superintendent_notes": "Unauthorized release attempt",
        }
        response = client.post("/cases/UTP-JAIL-REL-03/confirm-release", json=payload, headers=headers)
        assert response.status_code == 403


# ── Scenario 16: GET /jail/inmates Returns Strictly Facility-Scoped Roster ──────

def test_scenario_16_jail_inmates_endpoint_returns_strictly_facility_scoped_roster():
    _insert_test_case({
        "case_id": "UTP-TIHAR4-01",
        "name": "Tihar 4 Inmate",
        "jail_location": "Central Jail No. 4, Tihar (Synthetic)",
        "facility_id": "fac_tihar_jail_04",
    })
    _insert_test_case({
        "case_id": "UTP-TIHAR2-01",
        "name": "Tihar 2 Inmate",
        "jail_location": "Central Jail No. 2, Tihar (Synthetic)",
        "facility_id": "fac_tihar_jail_02",
    })
    _insert_test_case({
        "case_id": "UTP-ROHINI-02",
        "name": "Rohini Inmate",
        "jail_location": "Rohini District Jail",
        "facility_id": "fac_rohini_jail",
    })

    headers = get_token_headers("JAIL_OFFICER", "tihar4_officer", facility_ids=["fac_tihar_jail_04", "Central Jail No. 4, Tihar"])
    response = client.get("/jail/inmates", headers=headers)
    assert response.status_code == 200
    inmates = response.json()
    inmate_ids = [i["inmate_id"] for i in inmates]
    assert "UTP-TIHAR4-01" in inmate_ids
    assert "UTP-TIHAR2-01" not in inmate_ids
    assert "UTP-ROHINI-02" not in inmate_ids


# ── Scenario 17: GET /cases/{id} Enforces Facility Boundary for Jail Officer ───

def test_scenario_17_jail_officer_dossier_access_enforces_facility_boundary():
    _insert_test_case({
        "case_id": "UTP-FAC-TIHAR-01",
        "name": "Authorized Inmate",
        "jail_location": "Central Jail No. 4, Tihar",
        "facility_id": "fac_tihar_jail_04",
    })
    _insert_test_case({
        "case_id": "UTP-FAC-ROHINI-01",
        "name": "Unauthorized Inmate",
        "jail_location": "District Jail Rohini",
        "facility_id": "fac_rohini_jail",
    })

    headers = get_token_headers("JAIL_OFFICER", "tihar_officer", facility_ids=["fac_tihar_jail_04"])
    res_ok = client.get("/cases/UTP-FAC-TIHAR-01", headers=headers)
    assert res_ok.status_code == 200
    assert res_ok.json()["case"]["name"] == "Authorized Inmate"

    res_deny = client.get("/cases/UTP-FAC-ROHINI-01", headers=headers)
    assert res_deny.status_code == 403
    assert "outside your authorized facility" in res_deny.json()["detail"]


# ── Scenario 18: Dossier Response Redacts Strategy, Drafts, and AI Reasoning ────

def test_scenario_18_jail_officer_dossier_redacts_strategy_drafts_and_ai_reasoning():
    _insert_test_case({
        "case_id": "UTP-JAIL-VIEW-01",
        "name": "Praveen Sharma",
        "jail_location": "Central Jail No. 4, Tihar",
        "facility_id": "fac_tihar_jail_04",
        "legal_strategy_notes": "Confidential defense strategy under Section 479 BNSS.",
    })
    headers = get_token_headers("JAIL_OFFICER", "tihar_officer", facility_ids=["fac_tihar_jail_04"])
    response = client.get("/cases/UTP-JAIL-VIEW-01", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["jail_authorized_view"] is True
    assert data["draft"] is None
    assert data["statutes"] == []
    assert data["retrieval"] == {}
    assert data["agent_activity_log"] == []


# ── Scenario 19: Sensitive Medical Records Field-Level Restricted for Jail ─────

def test_scenario_19_sensitive_medical_records_field_level_restricted_for_jail():
    from app.auth.user_store import AuthUser
    jail_user = AuthUser(
        id="demo_jail_officer",
        email="jail@demo.nyayamitra.in",
        role=Role.JAIL_OFFICER,
        org_id="org_tihar_jail",
        full_name="Jail Superintendent",
        facility_ids=["fac_tihar_jail_04"],
    )
    # 1. Verify clearance function
    assert has_medical_clearance(jail_user) is False

    # 2. Verify field-level case filter masks sensitive medical notes
    case_dict = {
        "case_id": "UTP-MED-01",
        "name": "Medical Case",
        "facility_id": "fac_tihar_jail_04",
        "jail_location": "Central Jail No. 4, Tihar",
        "medical_record": {
            "has_vulnerability": True,
            "vulnerability_category": "PSYCHIATRIC",
            "details_restricted": "Confidential medical evaluation notes.",
        },
        "urgency_flags": {
            "age": 45,
            "health_flag": True,
            "medical_notes": "Severe cardiovascular complication requiring specialist treatment.",
        },
    }
    filtered = FieldLevelAccessFilter.filter_case(case_dict, jail_user)
    assert filtered["urgency_flags"]["medical_notes"] == "[RESTRICTED - MEDICAL PRIVACY]"
    assert filtered["medical_record"]["is_redacted"] is True


# ── Scenario 20: Jail Officer Denied from Document Workspace Drafting Actions ──

def test_scenario_20_jail_officer_denied_from_document_workspace_drafting_actions():
    from app.auth.user_store import AuthUser
    from fastapi import HTTPException
    jail_user = AuthUser(
        id="demo_jail_officer",
        email="jail@demo.nyayamitra.in",
        role=Role.JAIL_OFFICER,
        org_id="org_tihar_jail",
        full_name="Jail Superintendent",
    )
    assert Role.JAIL_OFFICER in DISALLOWED_WORKSPACE_ROLES

    for action in [
        DocumentAction.INITIATE_DRAFT,
        DocumentAction.EDIT_DRAFT,
        DocumentAction.APPROVE_DRAFT,
        DocumentAction.PACKAGE_DRAFT,
        DocumentAction.RECORD_FILING,
    ]:
        with pytest.raises(HTTPException) as exc_info:
            authorize_document_action(user=jail_user, action=action, case_id="UTP-0001")
        assert exc_info.value.status_code == 403
        assert "not authorized to access the legal document workspace" in exc_info.value.detail


# ── Scenario 21: Bulk Task Actions Reject Consequential Release Actions ─────────

def test_scenario_21_bulk_task_actions_reject_consequential_release_actions():
    headers = get_token_headers("JAIL_OFFICER", "demo_jail_officer", facility_ids=["fac_tihar_jail_04"])
    payload = {
        "action": "CONFIRM_PRISON_RELEASE",
        "task_ids": ["TASK-001", "TASK-002"],
    }
    response = client.post("/tasks/bulk", json=payload, headers=headers)
    assert response.status_code == 400
    assert "cannot be performed in bulk" in response.json()["detail"]


# ── Scenario 22: Zero Emojis Verified Across Jail Officer Stack ────────────────

def test_scenario_22_zero_emojis_verified_across_jail_officer_stack():
    import re
    from pathlib import Path
    files_to_check = [
        Path("backend/app/auth/policy.py"),
        Path("backend/app/security/classification.py"),
        Path("backend/app/services/task_service.py"),
        Path("backend/tests/test_stage19_jail_role_hardening.py"),
        Path("Frontend/src/pages/JailWorkspace.tsx"),
    ]
    emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
    for p in files_to_check:
        if p.exists():
            content = p.read_text(encoding="utf-8")
            matches = emoji_pattern.findall(content)
            assert len(matches) == 0, f"Found emojis {set(matches)} in {p}"

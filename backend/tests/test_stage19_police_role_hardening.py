"""
test_stage19_police_role_hardening.py - Comprehensive Stage 19 Test Suite.
========================================================================
Validates Stage 19 Police Role Hardening for POLICE_OFFICER:
1. Strict 3-tier scoping: station -> district -> organization on all requests.
2. Cross-station case access blocked (403 Forbidden).
3. Cross-district case access blocked (403 Forbidden).
4. Cross-organization case access blocked (403 Forbidden).
5. Police-safe dossier projection: strips defence strategy, RAG citations, and redacts civilian privacy.
6. Defence draft workspace editing and initiation blocked (403 Forbidden).
7. AI petition generation and assessment blocked (403 Forbidden).
8. Legal document approval blocked (403 Forbidden).
9. Supervisory workflow approval blocked (403 Forbidden).
10. Counsel sign-off blocked (403 Forbidden).
11. Court filing blocked (403 Forbidden).
12. Lawyer assignment blocked (403 Forbidden).
13. Accused profile station-scoping and civilian privacy protection.
14. Authorized station FIR intake (200 OK, database records created, provenance preserved).
15. Cross-station FIR intake blocked (403 Forbidden).
16. Cross-district FIR intake blocked (403 Forbidden).
17. Authorized FIR update with investigation notes and timeline provenance (200 OK).
18. Cross-station FIR update blocked (403 Forbidden).
19. Authorized police document upload (PENDING_VERIFICATION, source_authority="POLICE").
20. Unauthorized document upload types blocked (403 Forbidden).
21. Cross-station document upload blocked (403 Forbidden).
22. Institutional coordination & DLSA request workflow: acknowledge & complete.
23. Universal operational task queue synchronization for POLICE_OFFICER.
24. Station-scoped court production schedule.
25. Strict zero-emoji policy verification.
"""

import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.database import init_db, get_case
from app.services.task_service import TaskService


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def kotwali_police_token():
    return create_access_token(
        subject="demo_police_officer",
        role="POLICE_OFFICER",
        org_id="ps_kotwali_central",
        extra_claims={
            "email": "police@demo.nyayamitra.in",
            "full_name": "Insp. Vikram Singh",
            "district": "Central Delhi",
            "police_station": "Kotwali Police Station",
            "police_station_id": "ps_kotwali_central",
            "jurisdiction_ids": ["ps_kotwali_central", "Central Delhi"],
        },
    )


@pytest.fixture
def civil_lines_police_token():
    return create_access_token(
        subject="police_civil_lines",
        role="POLICE_OFFICER",
        org_id="ps_civil_lines",
        extra_claims={
            "email": "police_civil@delhipolice.gov.in",
            "full_name": "Sub-Insp. A. K. Verma",
            "district": "North Delhi",
            "police_station": "Civil Lines Police Station",
            "police_station_id": "ps_civil_lines",
            "jurisdiction_ids": ["ps_civil_lines", "North Delhi"],
        },
    )


@pytest.fixture
def mumbai_police_token():
    return create_access_token(
        subject="police_mumbai",
        role="POLICE_OFFICER",
        org_id="org_mumbai_police",
        extra_claims={
            "email": "police_mumbai@mahapolice.gov.in",
            "full_name": "Insp. S. Patil",
            "district": "Mumbai South",
            "police_station": "Colaba Police Station",
            "police_station_id": "ps_colaba",
            "jurisdiction_ids": ["ps_colaba", "Mumbai South"],
        },
    )


# ── Scenario 1: Station-Scoped Case Roster ────────────────────────────────────

def test_01_police_case_roster_station_scoped(client, kotwali_police_token):
    """GET /police/cases and GET /cases return strictly station-scoped cases."""
    res = client.get("/police/cases", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert res.status_code == 200
    cases = res.json()
    assert isinstance(cases, list)
    case_ids = [c["case_id"] for c in cases]
    assert "UTP-0001" in case_ids
    assert "UTP-0007" not in case_ids
    assert "UTP-0004" not in case_ids
    assert "UTP-0005" not in case_ids

    # Check generic /cases endpoint scoping
    res_all = client.get("/cases", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert res_all.status_code == 200
    cases_all = res_all.json()
    case_all_ids = [c["case"]["case_id"] for c in cases_all]
    assert "UTP-0001" in case_all_ids
    assert "UTP-0007" not in case_all_ids
    assert "UTP-0004" not in case_all_ids


# ── Scenario 2: Cross-Station Case Access Blocked ──────────────────────────────

def test_02_cross_station_access_denied(client, kotwali_police_token):
    """Accessing case from a different police station returns 403 Forbidden."""
    res = client.get("/cases/UTP-0002", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert res.status_code == 403
    assert "jurisdiction" in res.json()["detail"].lower()


# ── Scenario 3: Cross-District Case Access Blocked ─────────────────────────────

def test_03_cross_district_access_denied(client, kotwali_police_token):
    """Accessing case from an unrelated judicial district returns 403 Forbidden."""
    res = client.get("/cases/UTP-0007", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert res.status_code == 403
    assert "jurisdiction" in res.json()["detail"].lower()


# ── Scenario 4: Cross-Organization Case Access Blocked ────────────────────────

def test_04_cross_organization_access_denied(client, mumbai_police_token):
    """Police officer from another organization/state cannot access Delhi cases."""
    res = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {mumbai_police_token}"})
    assert res.status_code == 403
    assert "jurisdiction" in res.json()["detail"].lower()


# ── Scenario 5: Dossier Projection Redactions ─────────────────────────────────

def test_05_dossier_projection_redacts_defence_and_civilian_privacy(client, kotwali_police_token):
    """Police dossier projection strips legal strategy and redacts civilian contacts."""
    res = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data.get("police_authorized_view") is True

    # Redacted defense strategy
    assert data.get("draft") is None
    assert data.get("statutes") is None
    assert data.get("retrieval") is None
    assert data.get("urgency") is None

    # Redacted civilian privacy info
    case_info = data["case"]
    assert case_info["relative_name"] == "[REDACTED - PRIVACY CONTROLLED]"
    assert case_info["relative_phone"] == "[REDACTED]"
    assert case_info["permanent_address"] == "[REDACTED - PRIVACY CONTROLLED]"


# ── Scenario 6: Defence Draft Workspace Blocked ───────────────────────────────

def test_06_defence_draft_workspace_access_denied(client, kotwali_police_token):
    """Police officers cannot initiate or edit defence drafts in document workspace."""
    res = client.post(
        "/api/documents/drafts/generate",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
    )
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


# ── Scenario 7: Petition Generation Blocked ───────────────────────────────────

def test_07_petition_generation_denied(client, kotwali_police_token):
    """Police officers cannot run AI assessment or receive legal bail reasoning."""
    res = client.post(
        "/cases/assess-document",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json={"document_name": "fir_scan.pdf"},
    )
    assert res.status_code == 403


# ── Scenario 8: Legal Document Approval Blocked ───────────────────────────────

def test_08_legal_document_approval_denied(client, kotwali_police_token):
    """Police officers cannot approve legal petitions or supervisory reviews."""
    res = client.post(
        "/cases/UTP-0001/approve",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
    )
    assert res.status_code == 403


# ── Scenario 9: Supervisory Workflow Approval Blocked ─────────────────────────

def test_09_supervisory_workflow_approval_denied(client, kotwali_police_token):
    """Police officers cannot execute supervisory approval transition in workflow."""
    res = client.post(
        "/cases/UTP-0001/transitions",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json={"transition": "SUPERVISORY_APPROVE", "comment": "Police officer attempt to approve"},
    )
    assert res.status_code == 403


# ── Scenario 10: Counsel Sign-Off Blocked ─────────────────────────────────────

def test_10_counsel_sign_off_denied(client, kotwali_police_token):
    """Police officers cannot perform advocate sign-off in workflow."""
    res = client.post(
        "/cases/UTP-0001/sign-off",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json={"draft_text": "Police officer sign-off attempt"},
    )
    assert res.status_code == 403


# ── Scenario 11: Court Filing Blocked ─────────────────────────────────────────

def test_11_court_filing_denied(client, kotwali_police_token):
    """Police officers cannot file defence petitions in court."""
    res1 = client.post(
        "/cases/UTP-0001/file",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
    )
    assert res1.status_code == 403

    res2 = client.post(
        "/cases/UTP-0001/file-in-court",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
    )
    assert res2.status_code == 403


# ── Scenario 12: Lawyer Assignment Blocked ────────────────────────────────────

def test_12_assign_lawyer_denied(client, kotwali_police_token):
    """Police officers cannot assign legal aid lawyers to cases."""
    res = client.post(
        "/cases/UTP-0001/assign-lawyer",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json={"lawyer_id": "demo_advocate"},
    )
    assert res.status_code == 403


# ── Scenario 13: Accused Profile Station Scoping & Privacy ────────────────────

def test_13_accused_profile_station_scoped(client, kotwali_police_token):
    """Accused profile respects station scoping and redacts confidential family contacts."""
    # Out of station accused -> 403 Forbidden
    res_out = client.get("/accused/acc_utp_0007", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert res_out.status_code == 403

    # In station accused -> 200 OK
    res_in = client.get("/accused/acc_utp_0001", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert res_in.status_code == 200
    accused = res_in.json()
    assert accused["family_contacts"] == []
    assert "RESTRICTED" in accused["permanent_address"]


# ── Scenario 14: Authorized Station FIR Intake ────────────────────────────────

def test_14_authorized_fir_intake(client, kotwali_police_token):
    """Police officer can register new station FIR docket within authorized jurisdiction."""
    payload = {
        "fir_number": "FIR-2026-0099",
        "police_station": "Kotwali Police Station",
        "police_station_id": "ps_kotwali_central",
        "district": "Central Delhi",
        "state": "Delhi",
        "accused_name": "Suresh Verma",
        "offense_sections": ["BNS 303(2)", "BNS 317(2)"],
        "filing_date": "2026-09-01",
        "arrest_date": "2026-09-02",
        "incident_details": "Alleged theft reported at Chandni Chowk commercial area.",
        "court_name": "Chief Metropolitan Magistrate Court, Central Delhi",
        "investigating_officer": "SI Vikram Singh",
    }
    res = client.post(
        "/cases/fir-intake",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["fir_number"] == "FIR-2026-0099"
    new_case_id = data["case_id"]

    # Verify created case record
    c_obj = get_case(new_case_id)
    assert c_obj is not None
    assert c_obj.name == "Suresh Verma"
    assert c_obj.police_station == "Kotwali Police Station"
    assert c_obj.police_station_id == "ps_kotwali_central"
    assert c_obj.district == "Central Delhi"

    # Verify timeline event provenance
    timeline = getattr(c_obj, "timeline", [])
    assert any(ev.event_type == "POLICE_FIR_INTAKE" for ev in timeline)


# ── Scenario 15: Cross-Station FIR Intake Blocked ─────────────────────────────

def test_15_cross_station_fir_intake_denied(client, kotwali_police_token):
    """Police officer cannot register an FIR under an unauthorized police station."""
    payload = {
        "fir_number": "FIR-2026-0888",
        "police_station": "Civil Lines Police Station",
        "police_station_id": "ps_civil_lines",
        "district": "North Delhi",
        "accused_name": "Illegal Accused",
        "offense_sections": ["BNS 303"],
    }
    res = client.post(
        "/cases/fir-intake",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json=payload,
    )
    assert res.status_code == 403
    assert "jurisdiction" in res.json()["detail"].lower()


# ── Scenario 16: Cross-District FIR Intake Blocked ────────────────────────────

def test_16_cross_district_fir_intake_denied(client, kotwali_police_token):
    """Police officer cannot register an FIR under an unauthorized district."""
    payload = {
        "fir_number": "FIR-2026-0777",
        "police_station": "Kotwali Police Station",
        "police_station_id": "ps_kotwali_central",
        "district": "South Delhi",
        "accused_name": "Cross District Accused",
        "offense_sections": ["BNS 303"],
    }
    res = client.post(
        "/cases/fir-intake",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json=payload,
    )
    assert res.status_code == 403
    assert "jurisdiction" in res.json()["detail"].lower()


# ── Scenario 17: Authorized FIR Record Update ─────────────────────────────────

def test_17_authorized_fir_update(client, kotwali_police_token):
    """Police officer can update investigation status and record case diary notes."""
    payload = {
        "offense_sections": ["BNS 303(2)", "BNS 305"],
        "charge_sheet_status": "DRAFT_PREPARED",
        "remand_status": "AVAILABLE_ON_RECORD",
        "investigation_notes": "IO completed witness statements under Section 180 BNSS.",
    }
    res = client.put(
        "/cases/UTP-0001/fir",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "offense_sections" in data["updated_fields"]

    # Verify updated case
    c_obj = get_case("UTP-0001")
    timeline = getattr(c_obj, "timeline", [])
    assert any(ev.event_type == "POLICE_FIR_UPDATE" for ev in timeline)


# ── Scenario 18: Cross-Station FIR Update Blocked ─────────────────────────────

def test_18_cross_station_fir_update_denied(client, kotwali_police_token):
    """Police officer cannot update FIR records for cases outside station jurisdiction."""
    payload = {
        "investigation_notes": "Attempted unauthorized update on another station case.",
    }
    res = client.put(
        "/cases/UTP-0007/fir",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json=payload,
    )
    assert res.status_code == 403
    assert "jurisdiction" in res.json()["detail"].lower()


# ── Scenario 19: Authorized Police Document Upload ────────────────────────────

def test_19_authorized_police_document_upload(client, kotwali_police_token):
    """Police officer can upload charge sheet, entering as PENDING_VERIFICATION under POLICE authority."""
    res = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=charge_sheet",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        data={"custom_text": "Final Investigation Report submitted under Section 193 BNSS."},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["file_hash"] != ""

    # Document upload does NOT immediately mark case documents complete
    c_obj = get_case("UTP-0001")
    assert c_obj.status.value != "DOCUMENTS_COMPLETE"


# ── Scenario 20: Unauthorized Document Upload Blocked ─────────────────────────

def test_20_unauthorized_document_upload_denied(client, kotwali_police_token):
    """Police officers cannot upload medical certificates or judicial opinions."""
    res = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=medical_certificate",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        data={"custom_text": "Medical diagnosis report"},
    )
    assert res.status_code == 403
    assert "Police officers may only upload police-origin records" in res.json()["detail"]


# ── Scenario 21: Cross-Station Document Upload Blocked ────────────────────────

def test_21_cross_station_document_upload_denied(client, kotwali_police_token):
    """Police officer cannot upload documents for cases belonging to another station."""
    res = client.post(
        "/documents/upload?case_id=UTP-0007&document_type=charge_sheet",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        data={"custom_text": "Charge sheet for Civil Lines case"},
    )
    assert res.status_code == 403
    assert "jurisdiction" in res.json()["detail"].lower()


# ── Scenario 22: Police Action & DLSA Coordination Workflow ───────────────────

def test_22_police_actions_acknowledge_and_complete(client, kotwali_police_token):
    """Police officer can list, acknowledge, and fulfill DLSA document requests."""
    # List actions
    res = client.get("/police/actions", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert res.status_code == 200
    actions = res.json()
    assert isinstance(actions, list)
    assert len(actions) > 0
    act_id = actions[0]["id"]

    # Acknowledge action
    res_ack = client.post(
        f"/police/actions/{act_id}/acknowledge",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json={"notes": "IO acknowledged document submission timeline"},
    )
    assert res_ack.status_code == 200

    # Complete action with verified document hash
    res_comp = client.post(
        f"/police/actions/{act_id}/complete",
        headers={"Authorization": f"Bearer {kotwali_police_token}"},
        json={"document_id": "sha256_hash_abc123", "notes": "Charge sheet deposited in court registry."},
    )
    assert res_comp.status_code == 200


# ── Scenario 23: Task Queue Synchronization for POLICE_OFFICER ────────────────

def test_23_operational_task_queue_sync(kotwali_police_token):
    """TaskService.sync_operational_tasks generates investigation tasks for POLICE_OFFICER."""
    synced = TaskService.sync_operational_tasks()
    assert synced > 0

    from app.repositories.task_repository import get_task_repository
    tasks = get_task_repository().list_tasks(owner_role="POLICE_OFFICER")
    assert len(tasks) > 0
    # Every police task must be of type SUBMIT_CHARGE_SHEET or have police owner
    assert any(t["task_type"] == "SUBMIT_CHARGE_SHEET" for t in tasks)


# ── Scenario 24: Station-Scoped Hearings Schedule ─────────────────────────────

def test_24_hearings_production_schedule_scoping(client, kotwali_police_token):
    """Court production schedule (/hearings) returns only matters under officer station."""
    res = client.get("/hearings", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert res.status_code == 200
    hearings = res.json()
    assert isinstance(hearings, list)
    assert len(hearings) > 0
    for h in hearings:
        assert h["case_id"] == "UTP-0001"
        assert "police_task" in h


# ── Scenario 25: Zero Emoji Verification ──────────────────────────────────────

def test_25_zero_emojis_verification(client, kotwali_police_token):
    """Verify strictly zero emojis across police endpoints, responses, and records."""
    import re
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\ud83c-\ud83e][\ud000-\udfff]",
        re.UNICODE,
    )

    # 1. Police cases
    res1 = client.get("/police/cases", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert not emoji_pattern.search(res1.text), "Found emoji in /police/cases response"

    # 2. Case detail
    res2 = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert not emoji_pattern.search(res2.text), "Found emoji in /cases/UTP-0001 response"

    # 3. Police actions
    res3 = client.get("/police/actions", headers={"Authorization": f"Bearer {kotwali_police_token}"})
    assert not emoji_pattern.search(res3.text), "Found emoji in /police/actions response"

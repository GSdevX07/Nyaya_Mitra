"""
tests/test_role_workspaces_and_scoping.py

Verifies:
1. Master case roster isolation (ACCUSED_USER & FAMILY_GUARDIAN blocked with 403).
2. Record-level scoping for advocates (assigned matters only).
3. Record-level scoping for police and jail officers.
4. Record-level authorization for individual case dossiers and accused profiles.
5. Legal knowledge governance permission matrix (DLSA propose vs Supervisor approve/activate vs Advocate consumer).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.database import init_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def _auth_header(role: Role, user_id: str, email: str, linked_case_id: str = None, full_name: str = ""):
    claims = {
        "email": email,
        "full_name": full_name or f"{role.value} User",
    }
    if linked_case_id:
        claims["linked_case_id"] = linked_case_id
    token = create_access_token(
        subject=user_id,
        role=role.value,
        org_id="org_dlsa_central",
        extra_claims=claims,
    )
    return {"Authorization": f"Bearer {token}"}


# ── 1. Master Case Roster Record-Level Scoping ────────────────────────────────

def test_citizen_cannot_access_master_case_roster():
    """ACCUSED_USER must be denied access to the master cases queue with HTTP 403."""
    headers = _auth_header(Role.ACCUSED_USER, "demo_accused", "accused@demo.nyayamitra.in", linked_case_id="UTP-0001")
    resp = client.get("/cases", headers=headers)
    assert resp.status_code == 403


def test_family_cannot_access_master_case_roster():
    """FAMILY_GUARDIAN must be denied access to the master cases queue with HTTP 403."""
    headers = _auth_header(Role.FAMILY_GUARDIAN, "demo_family", "family@demo.nyayamitra.in", linked_case_id="UTP-0001")
    resp = client.get("/cases", headers=headers)
    assert resp.status_code == 403


def test_dlsa_officer_can_access_cases():
    """DLSA_OFFICER can access the institutional case queue."""
    headers = _auth_header(Role.DLSA_OFFICER, "demo_dlsa", "dlsa@demo.nyayamitra.in")
    resp = client.get("/cases", headers=headers)
    assert resp.status_code == 200
    cases = resp.json()
    assert isinstance(cases, list)
    assert len(cases) > 0


def test_advocate_cases_are_scoped():
    """DEFENSE_ADVOCATE sees strictly assigned cases (unassigned pool removed)."""
    headers = _auth_header(
        Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in",
        full_name="Adv. Rajesh Sharma", linked_case_id="UTP-0001"
    )
    resp = client.get("/cases", headers=headers)
    assert resp.status_code == 200
    cases = resp.json()
    assert isinstance(cases, list)
    case_ids = [c["case"]["case_id"] for c in cases]
    assert all(cid == "UTP-0001" for cid in case_ids)


def test_external_advocate_strictly_scoped_to_assigned():
    """CONTROLLED_EXTERNAL_ADVOCATE receives only explicitly assigned cases."""
    headers = _auth_header(
        Role.CONTROLLED_EXTERNAL_ADVOCATE, "demo_ext_advocate", "extadvocate@demo.nyayamitra.in",
        full_name="External Counsel", linked_case_id="UTP-0001"
    )
    resp = client.get("/cases", headers=headers)
    assert resp.status_code == 200
    cases = resp.json()
    case_ids = [c["case"]["case_id"] for c in cases]
    assert all(cid == "UTP-0001" for cid in case_ids)


# ── 2. Case Dossier Individual Record-Level Authorization ─────────────────────

def test_accused_can_access_own_case_dossier():
    """ACCUSED_USER can access their own linked case dossier."""
    headers = _auth_header(Role.ACCUSED_USER, "demo_accused", "accused@demo.nyayamitra.in", linked_case_id="UTP-0001")
    resp = client.get("/citizen/my-case", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accused_name"] is not None


def test_accused_cannot_access_other_case_dossier():
    """ACCUSED_USER cannot access an unlinked case dossier."""
    headers = _auth_header(Role.ACCUSED_USER, "demo_accused", "accused@demo.nyayamitra.in", linked_case_id="UTP-0001")
    resp = client.get("/cases/UTP-0007", headers=headers)
    assert resp.status_code == 403


def test_external_advocate_cannot_access_unassigned_case():
    """CONTROLLED_EXTERNAL_ADVOCATE cannot access unassigned case dossier."""
    headers = _auth_header(
        Role.CONTROLLED_EXTERNAL_ADVOCATE, "demo_ext_advocate", "extadvocate@demo.nyayamitra.in",
        full_name="External Counsel", linked_case_id="UTP-0001"
    )
    resp = client.get("/cases/UTP-0007", headers=headers)
    assert resp.status_code == 403


# ── 3. Accused Person Profile Record-Level Authorization ──────────────────────

def test_accused_cannot_view_other_accused_profile():
    """ACCUSED_USER accessing another person's accused profile receives 403."""
    headers = _auth_header(Role.ACCUSED_USER, "demo_accused", "accused@demo.nyayamitra.in", linked_case_id="UTP-0001")
    resp = client.get("/accused/acc_utp_0007", headers=headers)
    assert resp.status_code == 403


def test_accused_cannot_view_other_accused_timeline():
    """ACCUSED_USER accessing another person's timeline receives 403."""
    headers = _auth_header(Role.ACCUSED_USER, "demo_accused", "accused@demo.nyayamitra.in", linked_case_id="UTP-0001")
    resp = client.get("/accused/acc_utp_0007/timeline", headers=headers)
    assert resp.status_code == 403


# ── 4. Legal Sources Governance Permissions ──────────────────────────────────

def test_dlsa_cannot_approve_legal_source():
    """DLSA_OFFICER cannot approve or activate a legal source (Supervisory / GovAdmin only)."""
    headers = _auth_header(Role.DLSA_OFFICER, "demo_dlsa", "dlsa@demo.nyayamitra.in")
    resp = client.patch("/api/legal-sources/SRC-BNSS-2023/lifecycle", headers=headers, json={"status": "approved", "review_notes": "Attempt"})
    assert resp.status_code == 403


def test_advocate_cannot_propose_or_approve_source():
    """DEFENSE_ADVOCATE is purely a consumer of legal knowledge; cannot mutate sources."""
    headers = _auth_header(Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in")
    resp = client.post("/api/legal-sources", headers=headers, json={
        "title": "Unauthorized Source",
        "short_name": "UNAUTH",
        "issuing_authority": "Self",
        "jurisdiction": "India",
        "effective_date": "2024-01-01",
        "legal_domain": "CRIMINAL_PROCEDURE",
        "raw_content": "Section 1",
    })
    assert resp.status_code == 403


def test_supervisor_can_govern_sources():
    """SUPERVISING_LEGAL_OFFICER can access legal source governance endpoints."""
    headers = _auth_header(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervisor", "supervisor@demo.nyayamitra.in")
    resp = client.get("/api/legal-sources", headers=headers)
    assert resp.status_code == 200
    sources = resp.json()
    assert isinstance(sources, list)


# ── 5. Police Hearings & Scoped Case Dossier Protection ───────────────────────

def test_police_officer_hearings_are_enriched_and_scoped():
    """POLICE_OFFICER hearings must be scoped to station/district and enriched with police tasks."""
    headers = _auth_header(Role.POLICE_OFFICER, "demo_police", "police@demo.nyayamitra.in")
    resp = client.get("/hearings", headers=headers)
    assert resp.status_code == 200
    hearings = resp.json()
    assert isinstance(hearings, list)
    assert len(hearings) > 0
    for h in hearings:
        # Must have police operational fields
        assert "id" in h
        assert "case_id" in h
        assert "prisoner_name" in h
        assert "court_name" in h
        assert "hearing_date" in h
        assert "hearing_type" in h
        assert "status" in h
        assert "fir_number" in h
        assert "police_task" in h


def test_police_officer_case_dossier_redactions():
    """POLICE_OFFICER accessing case dossier receives operational data with confidential info redacted."""
    headers = _auth_header(Role.POLICE_OFFICER, "demo_police", "police@demo.nyayamitra.in")
    resp = client.get("/cases/UTP-0001", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    
    # Check that confidential advocate strategy & drafts are strictly redacted
    assert data.get("draft") is None
    assert data.get("statutes") is None
    assert data.get("retrieval") is None
    assert data.get("agent_activity_log") == []
    
    # Check that family info is redacted
    c = data.get("case", {})
    assert "REDACTED" in c.get("relative_name", "")
    assert "REDACTED" in c.get("relative_phone", "")
    
    # Check that police operational particulars are preserved
    assert c.get("fir_number") is not None
    assert c.get("police_station") is not None
    assert c.get("arrest_date") is not None
    assert c.get("custody_days") is not None


# ── 6. Supervising Legal Officer Boundaries & Scoping ──────────────────────────

def test_supervisor_cannot_self_assign_case():
    """SUPERVISING_LEGAL_OFFICER cannot self-assign matters via /cases/{id}/take."""
    headers = _auth_header(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising", "supervisor@demo.nyayamitra.in")
    resp = client.post("/cases/UTP-0001/take", headers=headers)
    assert resp.status_code == 403


def test_dlsa_cannot_self_assign_case():
    """DLSA_OFFICER cannot self-assign matters as defense counsel."""
    headers = _auth_header(Role.DLSA_OFFICER, "demo_dlsa", "dlsa@demo.nyayamitra.in")
    resp = client.post("/cases/UTP-0001/take", headers=headers)
    assert resp.status_code == 403


def test_supervisor_case_roster_scoped_to_district():
    """SUPERVISING_LEGAL_OFFICER with Central Delhi receives only authorized district cases."""
    headers = _auth_header(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising", "supervisor@demo.nyayamitra.in")
    resp = client.get("/cases", headers=headers)
    assert resp.status_code == 200
    cases = resp.json()
    assert isinstance(cases, list)
    for entry in cases:
        c = entry["case"]
        is_central = c.get("district") and "central" in c["district"].lower()
        is_review_state = c.get("status") in ["LAWYER_REVIEW", "APPROVED_READY_FOR_FILING", "MANUAL_REVIEW"]
        assert is_central or is_review_state


def test_supervisor_cross_district_dossier_blocked():
    """SUPERVISING_LEGAL_OFFICER accessing unescalated case outside jurisdiction receives 403."""
    headers = _auth_header(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising", "supervisor@demo.nyayamitra.in")
    resp = client.get("/cases/UTP-0007", headers=headers)
    assert resp.status_code == 403


def test_supervisor_authorized_district_dossier_accessible():
    """SUPERVISING_LEGAL_OFFICER accessing within-jurisdiction case dossier succeeds."""
    headers = _auth_header(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising", "supervisor@demo.nyayamitra.in")
    resp = client.get("/cases/UTP-0001", headers=headers)
    assert resp.status_code == 200


def test_supervisor_cannot_upload_primary_institutional_documents():
    """SUPERVISING_LEGAL_OFFICER cannot upload originating institutional records (remand, FIR, chargesheet)."""
    headers = _auth_header(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising", "supervisor@demo.nyayamitra.in")
    resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=remand_order",
        headers=headers,
        data={"custom_text": "Sample unauthorized remand order entry"},
    )
    assert resp.status_code == 403


def test_supervisor_can_upload_supervisory_review_note():
    """SUPERVISING_LEGAL_OFFICER can upload legitimate supervisory review notes."""
    headers = _auth_header(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising", "supervisor@demo.nyayamitra.in")
    resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=supervisory_review_note",
        headers=headers,
        data={"custom_text": "Supervisory compliance note: bail eligibility threshold verified under BNSS 479."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"


def test_supervisor_forbidden_actions_rejected():
    """SUPERVISING_LEGAL_OFFICER attempting judicial or court filing actions receives 403."""
    headers = _auth_header(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising", "supervisor@demo.nyayamitra.in")
    resp = client.post("/actions/trigger?action_id=ACT-UTP-0001-COURT_FILE", headers=headers)
    assert resp.status_code == 403


def test_approval_timeline_provenance_records_supervisor():
    """Approve case timeline event records actor_role=SUPERVISING_LEGAL_OFFICER, not defense advocate."""
    headers = _auth_header(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising", "supervisor@demo.nyayamitra.in", full_name="Dr. Aruna Roy")
    resp = client.post("/cases/UTP-0001/approve", headers=headers)
    assert resp.status_code == 200
    
    # Check timeline
    timeline_resp = client.get("/cases/UTP-0001/timeline", headers=headers)
    assert timeline_resp.status_code == 200
    events = timeline_resp.json().get("timeline", [])
    appr_events = [e for e in events if "Supervisory Sign-Off" in e.get("title", "")]
    assert len(appr_events) > 0
    assert appr_events[-1]["actor_role"] == "SUPERVISING_LEGAL_OFFICER"


def test_evidence_verify_returns_integrity_verified():
    """Evidence verify returns status=INTEGRITY_VERIFIED, not misleading 'Verified Authentic'."""
    headers = _auth_header(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising", "supervisor@demo.nyayamitra.in")
    # Verify existing evidence item for UTP-0001
    resp = client.post("/evidence/verify?evidence_id=EVD-UTP-0001-remand_order", headers=headers)
    if resp.status_code == 404:
        # Check all evidence items to find a valid id
        ev_list = client.get("/evidence", headers=headers).json()
        if ev_list:
            ev_id = ev_list[0]["id"]
            resp = client.post(f"/evidence/verify?evidence_id={ev_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["INTEGRITY_VERIFIED", "INTEGRITY_VIOLATION"]


# ── 7. Defense Legal-Aid Advocate Boundaries & Scoping ─────────────────────────

def test_advocate_cannot_access_unassigned_case_dossier():
    """DEFENSE_ADVOCATE cannot access case dossier of an unassigned case."""
    headers = _auth_header(
        Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in",
        full_name="Adv. Rajesh Sharma", linked_case_id="UTP-0001"
    )
    resp = client.get("/cases/UTP-0007", headers=headers)
    assert resp.status_code == 403


def test_advocate_can_access_assigned_case_dossier():
    """DEFENSE_ADVOCATE can access case dossier of an assigned case."""
    headers = _auth_header(
        Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in",
        full_name="Adv. Rajesh Sharma", linked_case_id="UTP-0001"
    )
    resp = client.get("/cases/UTP-0001", headers=headers)
    assert resp.status_code == 200


def test_advocate_cannot_access_unassigned_accused_profile():
    """DEFENSE_ADVOCATE cannot view profile of an accused person not assigned to them."""
    headers = _auth_header(
        Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in",
        full_name="Adv. Rajesh Sharma", linked_case_id="UTP-0001"
    )
    resp = client.get("/accused/acc_utp_0007", headers=headers)
    assert resp.status_code == 403


def test_advocate_can_access_assigned_accused_profile():
    """DEFENSE_ADVOCATE can view profile of an accused person connected to their assigned case."""
    headers = _auth_header(
        Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in",
        full_name="Adv. Rajesh Sharma", linked_case_id="UTP-0001"
    )
    resp = client.get("/accused/acc_utp_0001", headers=headers)
    assert resp.status_code == 200


def test_advocate_cannot_access_unassigned_accused_timeline():
    """DEFENSE_ADVOCATE cannot view chronological timeline of an unassigned accused individual."""
    headers = _auth_header(
        Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in",
        full_name="Adv. Rajesh Sharma", linked_case_id="UTP-0001"
    )
    resp = client.get("/accused/acc_utp_0007/timeline", headers=headers)
    assert resp.status_code == 403


def test_advocate_hearings_are_strictly_scoped():
    """DEFENSE_ADVOCATE receives only hearings for their assigned cases."""
    headers = _auth_header(
        Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in",
        full_name="Adv. Rajesh Sharma", linked_case_id="UTP-0001"
    )
    resp = client.get("/hearings", headers=headers)
    assert resp.status_code == 200
    hearings = resp.json()
    assert isinstance(hearings, list)
    for h in hearings:
        assert h.get("case_id") == "UTP-0001"


def test_advocate_documents_are_strictly_scoped():
    """DEFENSE_ADVOCATE receives only documents for their assigned cases."""
    headers = _auth_header(
        Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in",
        full_name="Adv. Rajesh Sharma", linked_case_id="UTP-0001"
    )
    resp = client.get("/documents", headers=headers)
    assert resp.status_code == 200
    docs = resp.json()
    assert isinstance(docs, list)
    for d in docs:
        assert d.get("case_id") == "UTP-0001"


def test_advocate_cannot_trigger_unassigned_case_action():
    """DEFENSE_ADVOCATE attempting to trigger action on unassigned case receives 403."""
    headers = _auth_header(
        Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in",
        full_name="Adv. Rajesh Sharma", linked_case_id="UTP-0001"
    )
    resp = client.post("/actions/trigger?action_id=ACT-UTP-0007-BAIL", headers=headers)
    assert resp.status_code == 403


def test_advocate_cannot_trigger_unauthorized_action_type():
    """DEFENSE_ADVOCATE attempting non-counsel action types (e.g. court filing) receives 403."""
    headers = _auth_header(
        Role.DEFENSE_ADVOCATE, "demo_advocate", "advocate@demo.nyayamitra.in",
        full_name="Adv. Rajesh Sharma", linked_case_id="UTP-0001"
    )
    resp = client.post("/actions/trigger?action_id=ACT-UTP-0001-COURT_FILE", headers=headers)
    assert resp.status_code == 403


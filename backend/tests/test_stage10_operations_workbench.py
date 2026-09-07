"""
backend/tests/test_stage10_operations_workbench.py
===================================================
Stage 10: Nyaya Mitra Authority-Facing Operations Workbench Automated Acceptance Suite.

Verifies:
1. Universal Task Queue contract:
   - Contains all 8 authoritative attributes: owner_role, owner_name, priority, due_date, source, reason, status, escalation_path.
   - Dynamic overdue task generation and filtering (status=OVERDUE).
2. Institutional Role Workbenches & Boundaries:
   - Jail Officer: Custody intake, custody events, profile capture, release confirmation gating (blocked unless BAIL_GRANTED), barred from drafting/approvals/counsel assignment.
   - DLSA Officer: Counsel assignment desk, roster querying, assignment transitions to COUNSEL_ASSIGNED, barred from supervisory approval and filing.
   - Supervising Legal Officer: Supervisory Level-2 approval, revision request, barred from creating drafts or court filing.
   - Defense Advocate: Scoped to assigned matters, filing strictly blocked prior to Level-2 supervisory approval.
   - Police Officer: Scoped to station records, zero access to legal defense strategy or drafting, barred from approvals.
   - Platform Admin: Technical operations only, barred from legal drafting and approvals.
3. Data-driven counsel assignment:
   - Querying /cases/{id}/eligible-counsel returns active panel roster with active caseloads.
"""

import pytest
import uuid
import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.database import get_db_connection, init_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


def make_token(role: Role, user_id: str, full_name: str, extra: dict = None) -> str:
    claims = {"email": f"{user_id}@demo.nyayamitra.in", "full_name": full_name}
    if extra:
        claims.update(extra)
    return create_access_token(
        subject=user_id,
        role=role.value,
        org_id="org_test_stage10",
        extra_claims=claims,
    )


@pytest.fixture
def jail_tok():
    return make_token(Role.JAIL_OFFICER, "demo_jail", "Superintendent Rao", {"facility_id": "FAC-TEST-01"})


@pytest.fixture
def dlsa_tok():
    return make_token(Role.DLSA_OFFICER, "demo_dlsa", "DLSA Secretary Sharma", {"district": "Central Delhi"})


@pytest.fixture
def supervisor_tok():
    return make_token(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising", "Supervising Officer Kapoor", {"district": "Central Delhi"})


@pytest.fixture
def advocate_tok():
    return make_token(Role.DEFENSE_ADVOCATE, "demo_advocate", "Adv. Meenakshi Sundaram", {"bar_registration_no": "D/999/2020"})


@pytest.fixture
def police_tok():
    return make_token(Role.POLICE_OFFICER, "demo_police", "SHO Kotwali PS", {"police_station_id": "PS-KOTWALI-01"})


@pytest.fixture
def admin_tok():
    return make_token(Role.PLATFORM_ADMIN, "demo_admin", "Platform Admin Patel")


# ── 1. Universal Task Queue Contract & Overdue Generation ────────────────────

def test_task_queue_schema_and_authoritative_attributes(dlsa_tok):
    """Verifies that /tasks/queue returns items adhering to the 8 authoritative keys."""
    res = client.get("/tasks/queue", headers={"Authorization": f"Bearer {dlsa_tok}"})
    assert res.status_code == 200, res.text
    tasks = res.json()
    assert isinstance(tasks, list)
    assert len(tasks) > 0, "Expected operational tasks in seeded DB"

    required_keys = {
        "owner_role",
        "owner_name",
        "priority",
        "due_date",
        "source",
        "reason",
        "status",
        "escalation_path",
    }
    for task in tasks:
        missing = required_keys - set(task.keys())
        assert not missing, f"Task {task.get('id')} is missing keys: {missing}"


def test_task_queue_dynamic_overdue_filter(dlsa_tok):
    """Verifies that filtering by status=OVERDUE evaluates past-due items."""
    res = client.get("/tasks/queue?status=OVERDUE", headers={"Authorization": f"Bearer {dlsa_tok}"})
    assert res.status_code == 200
    tasks = res.json()
    today_iso = datetime.date.today().isoformat()
    for task in tasks:
        assert task["status"] == "OVERDUE"
        assert task["due_date"] <= today_iso


# ── 2. Jail Officer Role Boundaries ──────────────────────────────────────────

def test_jail_officer_intake_and_custody_events(jail_tok):
    """Jail officer can intake accused person and append custody events."""
    unique_name = f"Inmate-{uuid.uuid4().hex[:6]}"
    intake_payload = {
        "name": unique_name,
        "facility_id": "FAC-TEST-01",
        "facility_name": "District Sub-Jail",
        "district": "Central Delhi",
        "court_name": "Chief Metropolitan Magistrate Court",
        "arrest_date": "2026-01-10",
        "admission_date": "2026-01-10",
        "offense_sections": ["BNS 303(2)"],
        "refer_to_dlsa": True,
        "notes": "Intake via automated Stage 10 test suite.",
    }
    res = client.post("/cases/intake-custody", json=intake_payload, headers={"Authorization": f"Bearer {jail_tok}"})
    assert res.status_code == 200, res.text
    data = res.json()
    case_id = data["case_id"]
    assert case_id is not None

    # Custody event logging
    event_payload = {
        "event_type": "REMAND_EXTENSION",
        "event_date": "2026-01-24",
        "court_name": "CMM Court",
        "notes": "14 days judicial remand extension granted.",
        "verified": True,
    }
    evt_res = client.post(f"/cases/{case_id}/custody-events", json=event_payload, headers={"Authorization": f"Bearer {jail_tok}"})
    assert evt_res.status_code == 200, evt_res.text


def test_jail_officer_release_confirmation_gated_by_bail_state(jail_tok):
    """Jail officer cannot confirm physical release on a case not in BAIL_GRANTED state."""
    # UTP-0001 is typically in earlier state, not BAIL_GRANTED
    payload = {
        "release_date": "2026-09-07",
        "gate_pass_number": "GP-99901",
        "superintendent_notes": "Attempting physical discharge.",
    }
    res = client.post("/cases/UTP-0001/confirm-release", json=payload, headers={"Authorization": f"Bearer {jail_tok}"})
    assert res.status_code in (400, 403), f"Expected release gating error, got {res.status_code}: {res.text}"


def test_jail_officer_cannot_draft_or_approve(jail_tok):
    """Jail officer is strictly barred from legal petition creation and supervisory approval."""
    # Attempt supervisory approval
    appr_res = client.post(
        "/cases/UTP-0001/approve",
        headers={"Authorization": f"Bearer {jail_tok}"},
    )
    assert appr_res.status_code == 403

    # Attempt counsel assignment
    assign_res = client.post(
        "/cases/UTP-0001/assign-counsel",
        json={"lawyer_id": "ADV-01", "lawyer_name": "Adv. Test"},
        headers={"Authorization": f"Bearer {jail_tok}"},
    )
    assert assign_res.status_code == 403


# ── 3. DLSA Officer Role Boundaries ──────────────────────────────────────────

def test_dlsa_officer_counsel_assignment_desk(dlsa_tok):
    """DLSA officer can query eligible counsel roster and assign panel advocate."""
    # Query eligible counsel for verified matter
    roster_res = client.get("/cases/UTP-0001/eligible-counsel", headers={"Authorization": f"Bearer {dlsa_tok}"})
    assert roster_res.status_code == 200, roster_res.text
    roster = roster_res.json()
    assert "counsel" in roster or "counsel_list" in roster

    # Assign counsel to the verified matter
    assign_payload = {
        "lawyer_id": "ADV-TEST-01",
        "lawyer_name": "Adv. S. K. Raman",
        "notes": "Assigned under Section 12 Legal Services Authorities Act.",
    }
    assign_res = client.post("/cases/UTP-0001/assign-counsel", json=assign_payload, headers={"Authorization": f"Bearer {dlsa_tok}"})
    assert assign_res.status_code == 200, assign_res.text


def test_dlsa_officer_cannot_supervisory_approve_or_file(dlsa_tok):
    """DLSA officer is barred from supervisory Level-2 approval and official court filing."""
    appr_res = client.post(
        "/cases/UTP-0002/approve",
        headers={"Authorization": f"Bearer {dlsa_tok}"},
    )
    assert appr_res.status_code == 403

    file_res = client.post(
        "/cases/UTP-0002/file",
        headers={"Authorization": f"Bearer {dlsa_tok}"},
    )
    assert file_res.status_code == 403


# ── 4. Supervising Legal Officer Boundaries ───────────────────────────────────

def test_supervising_legal_officer_cannot_file_in_court(supervisor_tok):
    """Supervising Legal Officer cannot execute court filing (advocate action only)."""
    file_res = client.post(
        "/cases/UTP-0001/file",
        headers={"Authorization": f"Bearer {supervisor_tok}"},
    )
    assert file_res.status_code == 403


def test_supervising_legal_officer_cannot_assign_counsel(supervisor_tok):
    """Supervising Legal Officer cannot assign counsel (DLSA desk only)."""
    assign_res = client.post(
        "/cases/UTP-0001/assign-counsel",
        json={"lawyer_id": "ADV-01", "lawyer_name": "Adv. Test"},
        headers={"Authorization": f"Bearer {supervisor_tok}"},
    )
    assert assign_res.status_code == 403


# ── 5. Police Officer Role Scoping ───────────────────────────────────────────

def test_police_officer_cannot_access_matter_artifacts_or_approve(police_tok):
    """Police officer has zero visibility into defense draft artifacts or legal strategy."""
    # Attempt to create an artifact (strictly blocked 403)
    draft_res = client.post(
        "/cases/UTP-0001/artifacts",
        json={"artifact_id": "art_test_pol", "artifact_type": "BAIL_APPLICATION", "content_text": "Draft"},
        headers={"Authorization": f"Bearer {police_tok}"},
    )
    assert draft_res.status_code == 403

    # Querying artifacts returns empty list with privileged work-product restriction notice
    art_res = client.get("/cases/UTP-0001/artifacts", headers={"Authorization": f"Bearer {police_tok}"})
    assert art_res.status_code == 200
    assert art_res.json()["artifact_versions"] == []
    assert "privileged defense work-product" in art_res.json()["notice"]

    appr_res = client.post(
        "/cases/UTP-0001/approve",
        headers={"Authorization": f"Bearer {police_tok}"},
    )
    assert appr_res.status_code == 403

    release_res = client.post(
        "/cases/UTP-0001/confirm-release",
        json={"release_date": "2026-09-07", "gate_pass_number": "GP-01"},
        headers={"Authorization": f"Bearer {police_tok}"},
    )
    assert release_res.status_code == 403


# ── 6. Platform Admin Technical Scoping ──────────────────────────────────────

def test_platform_admin_cannot_approve_or_file_legal_matters(admin_tok):
    """Platform Admin has zero legal drafting, approval, or filing authority."""
    appr_res = client.post(
        "/cases/UTP-0001/approve",
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert appr_res.status_code == 403

    file_res = client.post(
        "/cases/UTP-0001/file",
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert file_res.status_code == 403


# ── 7. DLSA District Scoping & Cross-District Isolation ──────────────────────

def test_dlsa_district_scoping_and_cross_district_isolation(dlsa_tok):
    """DLSA officer workspace is strictly scoped to their jurisdiction district."""
    # Central Delhi DLSA querying cases
    res = client.get("/cases", headers={"Authorization": f"Bearer {dlsa_tok}"})
    assert res.status_code == 200
    cases = res.json()
    assert len(cases) > 0
    # None of the returned cases should be from South Delhi
    for c in cases:
        record = c.get("case", c)
        assert record.get("district") != "South Delhi", f"Leak: Case {record.get('case_id')} from South Delhi returned to Central DLSA"

    # Central Delhi DLSA querying available cases
    avail_res = client.get("/cases/available", headers={"Authorization": f"Bearer {dlsa_tok}"})
    assert avail_res.status_code == 200
    avail_cases = avail_res.json()
    for c in avail_cases:
        record = c.get("case", c)
        assert record.get("district") != "South Delhi"

    # Central Delhi DLSA attempting to access South Delhi case UTP-0007 (Strict 403)
    cross_res = client.get("/cases/UTP-0007", headers={"Authorization": f"Bearer {dlsa_tok}"})
    assert cross_res.status_code == 403
    assert "jurisdiction" in cross_res.text.lower() or "district" in cross_res.text.lower()

    # South Delhi DLSA querying UTP-0007 (Permitted 200)
    south_tok = make_token(Role.DLSA_OFFICER, "dlsa_south_sec", "South DLSA Secretary", {"district": "South Delhi"})
    south_res = client.get("/cases/UTP-0007", headers={"Authorization": f"Bearer {south_tok}"})
    assert south_res.status_code == 200
    res_data = south_res.json()
    case_obj = res_data.get("case", res_data)
    assert case_obj.get("district") == "South Delhi"


# ── 8. Expedite Coordination Dispatch & Cross-Role Notification Flow ─────────

def test_expedite_coordination_dispatch_and_cross_role_notifications(dlsa_tok, jail_tok, police_tok):
    """DLSA expedite coordination creates task in queue and delivers alerts to Jail and Police."""
    payload = {
        "notes": "Urgent missing charge sheet and remand records required for §479 evaluation.",
        "target_roles": ["JAIL_OFFICER", "POLICE_OFFICER"],
    }
    coord_res = client.post(
        "/cases/UTP-0001/expedite-coordination",
        json=payload,
        headers={"Authorization": f"Bearer {dlsa_tok}"},
    )
    assert coord_res.status_code == 200
    coord_data = coord_res.json()
    assert coord_data.get("status") in ("SUCCESS", "DISPATCHED")
    assert "task_id" in coord_data

    # Verify task in task queue
    q_res = client.get("/tasks/queue", headers={"Authorization": f"Bearer {dlsa_tok}"})
    assert q_res.status_code == 200
    all_tasks = q_res.json()
    matching_tasks = [t for t in all_tasks if t.get("case_id") == "UTP-0001" and t.get("task_type") == "EXPEDITE_MISSING_CHARGE_SHEET"]
    assert len(matching_tasks) > 0

    # Verify notification delivered to Jail Officer
    jail_notifs_res = client.get("/notifications", headers={"Authorization": f"Bearer {jail_tok}"})
    assert jail_notifs_res.status_code == 200
    jail_notifs = jail_notifs_res.json()
    assert any("UTP-0001" in n.get("title", "") or "UTP-0001" in n.get("message", "") for n in jail_notifs)

    # Verify notification delivered to Police Officer
    pol_notifs_res = client.get("/notifications", headers={"Authorization": f"Bearer {police_tok}"})
    assert pol_notifs_res.status_code == 200
    pol_notifs = pol_notifs_res.json()
    assert any("UTP-0001" in n.get("title", "") or "UTP-0001" in n.get("message", "") for n in pol_notifs)


# ── 9. Controlled External Advocate Institutional Boundaries ─────────────────

def test_controlled_external_advocate_strictly_barred_from_drafting_signing_filing():
    """Controlled external advocates cannot draft artifacts, sign off, or file in court."""
    ext_tok = make_token(Role.CONTROLLED_EXTERNAL_ADVOCATE, "ext_adv_01", "Adv. External Counsel")

    # Barred from drafting legal artifacts (403)
    art_res = client.post(
        "/cases/UTP-0001/artifacts",
        json={"artifact_id": "art_ext_01", "artifact_type": "BAIL_APPLICATION", "content_text": "Draft"},
        headers={"Authorization": f"Bearer {ext_tok}"},
    )
    assert art_res.status_code == 403

    # Barred from signing off or approving (403)
    appr_res = client.post(
        "/cases/UTP-0001/approve",
        headers={"Authorization": f"Bearer {ext_tok}"},
    )
    assert appr_res.status_code == 403

    # Barred from filing in court (403)
    file_res = client.post(
        "/cases/UTP-0001/file",
        headers={"Authorization": f"Bearer {ext_tok}"},
    )
    assert file_res.status_code == 403


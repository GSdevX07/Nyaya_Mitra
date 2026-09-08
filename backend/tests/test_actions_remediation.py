"""
test_actions_remediation.py — Comprehensive validation of Legal Actions queue,
statutory filtering, role scoping, database persistence, and cross-authority handoffs.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.database import (
    init_db,
    get_db_connection,
    get_dispatched_actions_map,
    get_police_actions,
    get_case_bail_application,
)

init_db()
client = TestClient(app)


def _auth_headers(
    role: Role,
    user_id: str = "test_user",
    district: str = "Central Delhi",
    police_station_id: str = "ps_civil_lines",
    facility_ids: list[str] | None = None,
    linked_case_id: str | None = None,
) -> dict:
    if facility_ids is None and role == Role.JAIL_OFFICER:
        facility_ids = ["fac_tihar_jail_04", "Central Jail No. 4, Tihar (Synthetic)", "tihar"]
    token = create_access_token(
        subject=user_id,
        role=role.value,
        org_id="org_dlsa_central",
        facility_ids=facility_ids or [],
        extra_claims={
            "district": district,
            "police_station_id": police_station_id,
            "linked_case_id": linked_case_id,
        },
    )
    return {"Authorization": f"Bearer {token}"}


def test_inactive_released_cases_excluded_from_actions():
    """Verify that released or post-release cases (like REL-0042) are excluded from the actions queue."""
    headers = _auth_headers(Role.DLSA_OFFICER, "demo_dlsa", district="all")
    resp = client.get("/actions", headers=headers)
    assert resp.status_code == 200
    actions = resp.json()

    # Assert REL-0042 does not appear in actions
    rel_cases = [a for a in actions if "REL-0042" in a.get("id", "") or a.get("case_id") == "REL-0042"]
    assert len(rel_cases) == 0, f"Found unexpected actions for released case REL-0042: {rel_cases}"


def test_dlsa_officer_can_view_and_trigger_document_requisition():
    """Verify DLSA officer can trigger ACT-*-DOCS and it persists to dispatched_actions and police_actions."""
    headers = _auth_headers(Role.DLSA_OFFICER, "demo_dlsa", district="all")
    resp = client.get("/actions", headers=headers)
    assert resp.status_code == 200
    actions = resp.json()
    doc_actions = [a for a in actions if "-DOCS" in a.get("id", "")]
    assert len(doc_actions) > 0, "Expected at least one document requisition action"

    target_action = doc_actions[0]
    action_id = target_action["id"]
    case_id = target_action["case_id"]

    # Trigger action
    trig_resp = client.post(f"/actions/trigger?action_id={action_id}", headers=headers)
    assert trig_resp.status_code == 200
    res_data = trig_resp.json()
    assert res_data["status"] == "Executed Successfully"

    # Verify database persistence in dispatched_actions
    disp_map = get_dispatched_actions_map()
    assert action_id in disp_map, f"Action {action_id} not found in dispatched_actions ledger"
    assert disp_map[action_id]["status"] == "DISPATCHED"

    # Verify police_actions table has the requisition
    police_acts = get_police_actions()
    matching_police_acts = [p for p in police_acts if p["case_id"] == case_id]
    assert len(matching_police_acts) > 0, f"No police action created for case {case_id}"

    # Verify subsequent GET /actions reports is_dispatched=True
    resp2 = client.get("/actions", headers=headers)
    assert resp2.status_code == 200
    updated_actions = {a["id"]: a for a in resp2.json()}
    assert action_id in updated_actions
    assert updated_actions[action_id]["is_dispatched"] is True
    assert updated_actions[action_id]["status"] == "Dispatched"


def test_dlsa_officer_can_trigger_bail_draft_action():
    """Verify DLSA officer can trigger Section 479 auto-draft and it persists to bail_applications."""
    headers = _auth_headers(Role.DLSA_OFFICER, "demo_dlsa", district="all")
    resp = client.get("/actions", headers=headers)
    assert resp.status_code == 200
    bail_actions = [a for a in resp.json() if "-BAIL" in a.get("id", "")]
    assert len(bail_actions) > 0, "Expected at least one Section 479 bail action"

    target_action = bail_actions[0]
    action_id = target_action["id"]
    case_id = target_action["case_id"]

    trig_resp = client.post(f"/actions/trigger?action_id={action_id}", headers=headers)
    assert trig_resp.status_code == 200

    # Verify bail_applications updated in database
    bail_app = get_case_bail_application(case_id)
    assert bail_app is not None, f"No bail application found for case {case_id}"
    assert "Section 479" in (bail_app.get("petition_draft_text") or "")


def test_police_officer_actions_scoping():
    """Verify POLICE_OFFICER can access /actions and only sees station-relevant document requisitions."""
    headers = _auth_headers(Role.POLICE_OFFICER, "demo_police", police_station_id="ps_civil_lines")
    resp = client.get("/actions", headers=headers)
    assert resp.status_code == 200
    actions = resp.json()
    for a in actions:
        assert "-DOCS" in a["id"], f"Police officer received non-document action: {a['id']}"


def test_jail_officer_actions_scoping():
    """Verify JAIL_OFFICER can access /actions and only sees facility custodial requisitions."""
    headers = _auth_headers(Role.JAIL_OFFICER, "demo_jail")
    resp = client.get("/actions", headers=headers)
    assert resp.status_code == 200
    actions = resp.json()
    for a in actions:
        assert "-DOCS" in a["id"], f"Jail officer received non-document action: {a['id']}"


def test_all_institutional_roles_can_read_actions():
    """Verify all valid organizational roles can view /actions without receiving 403."""
    role_user_map = [
        (Role.DLSA_OFFICER, "demo_dlsa"),
        (Role.SUPERVISING_LEGAL_OFFICER, "demo_supervising"),
        (Role.DEFENSE_ADVOCATE, "demo_advocate"),
        (Role.CONTROLLED_EXTERNAL_ADVOCATE, "demo_external_advocate"),
        (Role.PLATFORM_ADMIN, "demo_admin"),
        (Role.GOV_ADMIN, "demo_gov"),
        (Role.READ_ONLY_AUDITOR, "demo_auditor"),
        (Role.POLICE_OFFICER, "demo_police"),
        (Role.JAIL_OFFICER, "demo_jail"),
    ]
    for role, uid in role_user_map:
        headers = _auth_headers(role, uid, district="all", linked_case_id="UTP-0001")
        resp = client.get("/actions", headers=headers)
        assert resp.status_code == 200, f"Role {role.value} failed to access /actions: {resp.status_code} {resp.text}"

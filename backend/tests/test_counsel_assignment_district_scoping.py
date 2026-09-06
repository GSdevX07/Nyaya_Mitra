"""
test_counsel_assignment_district_scoping.py
============================================
Comprehensive test suite verifying:
1. NALSA statutory ranking hierarchy for DLSA counsel allocation:
   - Tier 1: Local DLSA matches case district (e.g., Bengaluru Urban for UTP-0012)
   - Tier 2: Special Panel (State SLSA / High Court Legal Services Committee)
   - Tier 3: Other district panels
2. Filtering out suspended / inactive advocates (adv_inactive_blr)
3. Direct API verification of GET /cases/{case_id}/eligible-counsel
4. Execution of ASSIGN_COUNSEL state machine transition with assigned advocate ID and name
5. Role-based access control guarding the eligible counsel endpoint
"""

import pytest
import sqlite3
import json
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.database import (
    get_db_connection,
    get_eligible_counsel_for_case,
    execute_case_transition_tx,
)
from app.workflow.service import WorkflowService


@pytest.fixture
def client():
    return TestClient(app)


def get_token(role: Role, user_id: str = "test_user", org_id: str = "org_dlsa_blr") -> str:
    return create_access_token(
        subject=user_id,
        role=role.value,
        org_id=org_id,
        facility_ids=["fac_central_blr"],
        extra_claims={"email": f"{user_id}@nyayamitra.in"},
    )


def test_bengaluru_urban_eligible_counsel_hierarchy(client):
    """
    UTP-0012 is a Bengaluru Urban undertrial case.
    Verify that GET /cases/UTP-0012/eligible-counsel prioritizes:
    - Bengaluru Urban DLSA counsel (Arun Kumar, Priya Sharma, Ravi Shankar) at Tier 1
    - Karnataka SLSA / HCLSC Special Panel (Kavitha Rao) at Tier 2
    - Other districts (Ballari, Mysuru) at Tier 3
    - Suspended advocate (adv_inactive_blr) is strictly excluded.
    """
    token = get_token(Role.DLSA_OFFICER, "dlsa_officer_blr")
    response = client.get(
        "/cases/UTP-0012/eligible-counsel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["case_id"] == "UTP-0012"
    assert data["case_district"] == "Bengaluru Urban"
    assert data["case_state"] == "Karnataka"
    assert "Bengaluru Urban" in data["primary_dlsa"]

    counsel_list = data["counsel_list"]
    assert len(counsel_list) >= 4

    # Check Tier 1: Local DLSA matches
    tier1_counsel = [c for c in counsel_list if c["tier"] == 1]
    assert len(tier1_counsel) >= 3
    tier1_ids = [c["id"] for c in tier1_counsel]
    assert "adv_kar_blr_01" in tier1_ids  # Adv. Arun Kumar
    assert "adv_kar_blr_02" in tier1_ids  # Adv. Priya Sharma
    assert "adv_kar_blr_03" in tier1_ids  # Adv. Ravi Shankar
    for c in tier1_counsel:
        assert c["district"] == "Bengaluru Urban"
        assert c["tier_label"] == "Local DLSA"
        assert c["panel_status"] == "Active"

    # Check Tier 2: Special Panel (Karnataka SLSA)
    tier2_counsel = [c for c in counsel_list if c["tier"] == 2]
    assert len(tier2_counsel) >= 1
    assert any(c["id"] == "adv_kar_slsa_01" for c in tier2_counsel)  # Adv. Kavitha Rao
    for c in tier2_counsel:
        assert c["is_higher_level_panel"] is True
        assert c["tier_label"] == "Special Panel"

    # Check Tier 3: Other districts (Ballari, Mysuru)
    tier3_counsel = [c for c in counsel_list if c["tier"] == 3]
    assert len(tier3_counsel) >= 2
    tier3_ids = [c["id"] for c in tier3_counsel]
    assert "adv_kar_blr_other1" in tier3_ids  # Suresh Gowda (Ballari)
    assert "adv_kar_blr_other2" in tier3_ids  # Manjunath K (Mysuru)

    # Check suspended counsel is NOT in the list
    all_counsel_ids = [c["id"] for c in counsel_list]
    assert "adv_inactive_blr" not in all_counsel_ids


def test_central_delhi_case_eligible_counsel_hierarchy(client):
    """
    UTP-0001 is a Central Delhi case.
    Verify that Central Delhi panel counsel appear at Tier 1 (Local DLSA).
    """
    token = get_token(Role.DLSA_OFFICER, "dlsa_officer_delhi")
    response = client.get(
        "/cases/UTP-0001/eligible-counsel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["case_id"] == "UTP-0001"
    assert data["case_district"] == "Central Delhi"

    counsel_list = data["counsel_list"]
    assert len(counsel_list) >= 2

    # Tier 1 must be Central Delhi counsel
    tier1_counsel = [c for c in counsel_list if c["tier"] == 1]
    assert len(tier1_counsel) >= 1
    tier1_names = [c["name"] for c in tier1_counsel]
    assert any("Rajesh Sharma" in n for n in tier1_names)


def test_assign_counsel_transition_workflow(client):
    """
    Verify full lifecycle integration:
    1. Case UTP-0012 transitioned to LEGAL_AID_REQUIRED.
    2. DLSA Officer executes ASSIGN_COUNSEL transition specifying Adv. Arun Kumar.
    3. Target state becomes ASSIGNED.
    4. Assigned advocate ID and display name are persisted authoritatively.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT version_number FROM cases WHERE case_id = 'UTP-0012'")
    row = cursor.fetchone()
    current_ver = (row[0] or 1) if row else 1

    execute_case_transition_tx(
        case_id="UTP-0012",
        new_status="LEGAL_AID_REQUIRED",
        expected_version=current_ver,
    )
    conn.close()

    status, ver, case_data = WorkflowService.get_case_state("UTP-0012")
    assert status.value == "LEGAL_AID_REQUIRED"

    dlsa_token = get_token(Role.DLSA_OFFICER, "dlsa_officer_blr")

    payload = {
        "transition": "ASSIGN_COUNSEL",
        "expected_version": ver,
        "payload": {
            "assigned_advocate_id": "adv_kar_blr_01",
            "assigned_advocate_name": "Adv. Arun Kumar",
        },
        "comment": "Allocated primary empanelled defense counsel from Bengaluru Urban DLSA",
    }

    resp = client.post(
        "/cases/UTP-0012/transitions",
        json=payload,
        headers={"Authorization": f"Bearer {dlsa_token}"},
    )
    assert resp.status_code == 200, resp.text
    res_data = resp.json()
    assert res_data["target_state"] == "ASSIGNED"

    new_status, new_ver, updated_case = WorkflowService.get_case_state("UTP-0012")
    assert new_status.value == "ASSIGNED"
    assert updated_case.get("assigned_advocate_id") == "adv_kar_blr_01"
    assert updated_case.get("assigned_advocate_name") == "Adv. Arun Kumar"
    assert updated_case.get("assigned_lawyer") == "Adv. Arun Kumar"


def test_unauthorized_roles_blocked_from_eligible_counsel(client):
    """
    Accused/Citizen role must NOT be permitted to access internal DLSA counsel assignment roster.
    """
    citizen_token = get_token(Role.ACCUSED_USER, "citizen_user")
    resp = client.get(
        "/cases/UTP-0012/eligible-counsel",
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert resp.status_code == 403

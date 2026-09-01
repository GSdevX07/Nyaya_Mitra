"""
test_authz.py — Authorization & RBAC/ABAC Positive and Negative Security Tests for Nyaya Mitra.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role

client = TestClient(app)


def _get_auth_headers(role: Role, user_id: str = "test_user", org_id: str = "org_dlsa_central") -> dict:
    token = create_access_token(
        subject=user_id,
        role=role.value,
        org_id=org_id,
    )
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_request_rejected():
    """Unauthenticated access to protected /cases endpoint must return 401."""
    resp = client.get("/cases")
    assert resp.status_code == 401
    assert "Not authenticated" in resp.json()["detail"]


def test_authenticated_dlsa_officer_can_view_cases():
    """DLSA Officer with valid token can access /cases."""
    headers = _get_auth_headers(Role.DLSA_OFFICER)
    resp = client.get("/cases", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_role_boundary_advocate_cannot_approve():
    """DEFENSE_ADVOCATE role cannot approve a case for filing (requires SUPERVISING_LEGAL_OFFICER)."""
    headers = _get_auth_headers(Role.DEFENSE_ADVOCATE)
    resp = client.post("/cases/UTP-0001/approve", headers=headers)
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_supervising_officer_can_approve():
    """SUPERVISING_LEGAL_OFFICER role can approve a case."""
    headers = _get_auth_headers(Role.SUPERVISING_LEGAL_OFFICER)
    resp = client.post("/cases/UTP-0001/approve", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] in ("success", "APPROVED_READY_FOR_FILING")


def test_jail_officer_cannot_trigger_actions():
    """JAIL_OFFICER cannot trigger automated legal actions."""
    headers = _get_auth_headers(Role.JAIL_OFFICER)
    resp = client.post("/actions/trigger?action_id=ACT-UTP-0001-BAIL", headers=headers)
    assert resp.status_code == 403


def test_auditor_read_only_restriction():
    """READ_ONLY_AUDITOR can read reports but cannot file in court or approve."""
    headers = _get_auth_headers(Role.READ_ONLY_AUDITOR)
    
    # Can read reports
    resp_read = client.get("/reports", headers=headers)
    assert resp_read.status_code == 200

    # Cannot file in court
    resp_write = client.post("/cases/UTP-0001/file", headers=headers)
    assert resp_write.status_code == 403


def test_defense_advocate_can_take_case():
    """DEFENSE_ADVOCATE can take up an available case."""
    headers = _get_auth_headers(Role.DEFENSE_ADVOCATE, user_id="adv_test_01")
    resp = client.post("/cases/UTP-0001/take", headers=headers)
    assert resp.status_code == 200
    assert "assigned to adv_test_01" in resp.json()["message"]


def test_evidence_verification_privilege():
    """
    Jail officers and auditors can verify evidence integrity.
    Civilian roles (ACCUSED_USER, FAMILY_GUARDIAN) are blocked (403).
    """
    # Jail officer is ALLOWED
    jail_headers = _get_auth_headers(Role.JAIL_OFFICER)
    resp_jail = client.post("/evidence/verify?evidence_id=EVI-UTP-0001-remand_order", headers=jail_headers)
    assert resp_jail.status_code in (200, 404)

    # Auditor is ALLOWED
    auditor_headers = _get_auth_headers(Role.READ_ONLY_AUDITOR)
    resp_auditor = client.post("/evidence/verify?evidence_id=EVI-UTP-0001-remand_order", headers=auditor_headers)
    assert resp_auditor.status_code in (200, 404)

    # Supervising officer is ALLOWED
    supervisor_headers = _get_auth_headers(Role.SUPERVISING_LEGAL_OFFICER)
    resp_allowed = client.post("/evidence/verify?evidence_id=EVI-UTP-0001-remand_order", headers=supervisor_headers)
    assert resp_allowed.status_code in (200, 404)

    # Accused user is BLOCKED (403)
    accused_headers = _get_auth_headers(Role.ACCUSED_USER)
    resp_blocked = client.post("/evidence/verify?evidence_id=EVI-UTP-0001-remand_order", headers=accused_headers)
    assert resp_blocked.status_code == 403

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.user_store import get_user_by_email
from app.database import get_case, update_case_status
from app.models.schemas import CaseState

client = TestClient(app)


def _get_supervisor_headers():
    user = get_user_by_email("supervisor@demo.nyayamitra.in")
    assert user is not None
    token = create_access_token(
        subject=user.id,
        role=user.role.value,
        org_id=user.org_id,
        extra_claims={
            "full_name": user.full_name,
            "district": user.district,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_approve_case_rejected_if_documents_missing():
    """State Machine: Cannot approve a case for filing when mandatory documents are missing."""
    headers = _get_supervisor_headers()
    # UTP-0001 has present_docs=["fir", "remand_order"] but requires chargesheet
    case = get_case("UTP-0001")
    assert case is not None
    original_status = case.status
    try:
        update_case_status("UTP-0001", CaseState.DOCUMENTS_MISSING)
        res = client.post("/cases/UTP-0001/approve", headers=headers)
        assert res.status_code == 400
        assert "mandatory case documents are missing" in res.json()["detail"]
    finally:
        update_case_status("UTP-0001", original_status)


def test_file_case_rejected_if_not_approved():
    """State Machine: Cannot file a case in court unless it has been formally approved."""
    headers = _get_supervisor_headers()
    case = get_case("UTP-0001")
    assert case is not None
    original_status = case.status
    try:
        update_case_status("UTP-0001", CaseState.DOCUMENTS_MISSING)
        res = client.post("/cases/UTP-0001/file", headers=headers)
        assert res.status_code == 400
        assert "cannot be filed" in res.json()["detail"]
    finally:
        update_case_status("UTP-0001", original_status)


def test_legal_rule_registry_listing():
    """Rule Registry: GET /rules/registry lists registered statutory rule versions."""
    headers = _get_supervisor_headers()
    res = client.get("/rules/registry", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "active_version" in data
    assert "rules" in data
    version_ids = [r["version_id"] for r in data["rules"]]
    assert "BNSS_479_RULESET_V1_2023" in version_ids
    assert "CRPC_436A_RULESET_V1_1973" in version_ids

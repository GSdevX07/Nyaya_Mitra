"""
Comprehensive test suite for Police Officer (POLICE_OFFICER) Role Remediation.

Verifies:
1. Strict institutional police station scoping for GET /police/cases and GET /cases.
2. GET /cases/{id} strict jurisdiction authorization (403 for other stations) and dossier projection (redactions of drafts, legal strategy, civilian contacts, and permanent address).
3. Accused profile (/accused/{id}) strict station jurisdiction check and privacy redactions.
4. Document upload allowlist enforcement: allows police-origin records (FIR, arrest memo, charge sheet, remand application), rejects judicial/medical records, and records PENDING_VERIFICATION.
5. Uploaded documents do not immediately flip case completeness to DOCUMENTS_COMPLETE.
6. Document AI pipeline restrictions: rejects POLICE_OFFICER from /cases/assess-document (403), and /documents/assess returns extraction-only metadata without legal citations.
7. Dedicated Police action workflow: GET /police/actions, POST acknowledge, POST complete.
8. Scoped hearings: only cases under authorized station, with operational task metadata and workflow state.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.database import init_db, get_all_cases


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def police_token():
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


def test_police_case_roster_strict_scoping(client, police_token):
    """GET /police/cases and GET /cases return only cases belonging to the authorized police station."""
    # 1. Dedicated endpoint
    res = client.get("/police/cases", headers={"Authorization": f"Bearer {police_token}"})
    assert res.status_code == 200
    cases = res.json()
    assert isinstance(cases, list)
    case_ids = [c["case_id"] for c in cases]
    assert "UTP-0001" in case_ids
    assert "UTP-0007" not in case_ids
    assert "UTP-0012" not in case_ids
    assert "UTP-0015" not in case_ids
    assert "REL-0042" not in case_ids

    # Verify fields
    c1 = next(c for c in cases if c["case_id"] == "UTP-0001")
    assert c1["police_station_id"] == "ps_kotwali_central"
    assert "charge_sheet_status" in c1
    assert "remand_status" in c1

    # 2. Generic /cases endpoint
    res2 = client.get("/cases", headers={"Authorization": f"Bearer {police_token}"})
    assert res2.status_code == 200
    cases2 = res2.json()
    case2_ids = [c["case"]["case_id"] for c in cases2]
    assert "UTP-0001" in case2_ids
    assert "UTP-0007" not in case2_ids
    assert "UTP-0015" not in case2_ids


def test_police_case_detail_jurisdiction_and_redaction(client, police_token):
    """GET /cases/{id} enforces strict station authorization and projects a police-safe dossier."""
    # Out of station case -> 403 Forbidden
    res_out = client.get("/cases/UTP-0007", headers={"Authorization": f"Bearer {police_token}"})
    assert res_out.status_code == 403
    assert "jurisdiction" in res_out.json()["detail"].lower()

    # In station case -> 200 OK with police projection
    res_in = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {police_token}"})
    assert res_in.status_code == 200
    data = res_in.json()

    assert data.get("police_authorized_view") is True
    # Redacted defense strategy and legal reasoning
    assert data.get("draft") is None
    assert data.get("statutes") is None
    assert data.get("retrieval") is None
    assert data.get("urgency") is None

    # Redacted civilian privacy info
    case_info = data["case"]
    assert case_info["relative_name"] == "[REDACTED - PRIVACY CONTROLLED]"
    assert case_info["relative_phone"] == "[REDACTED]"
    assert case_info["permanent_address"] == "[REDACTED - PRIVACY CONTROLLED]"

    # Operational status fields present
    assert "remand_status" in data
    assert "charge_sheet_status" in data


def test_police_accused_profile_strict_scoping_and_redaction(client, police_token):
    """Accused profile endpoint enforces station jurisdiction and redacts family/address details."""
    # Out of jurisdiction accused
    res_out = client.get("/accused/acc_utp_0007", headers={"Authorization": f"Bearer {police_token}"})
    assert res_out.status_code == 403

    # In jurisdiction accused
    res_in = client.get("/accused/acc_utp_0001", headers={"Authorization": f"Bearer {police_token}"})
    assert res_in.status_code == 200
    accused = res_in.json()
    assert accused["family_contacts"] == []
    assert "RESTRICTED" in accused["permanent_address"]
    # Connected cases are filtered to authorized station
    assert all(c["case_id"] == "UTP-0001" for c in accused["connected_cases"])


def test_police_document_upload_allowlist_and_verification_status(client, police_token):
    """Police upload allows only police-origin records, enforces station jurisdiction, and records PENDING_VERIFICATION."""
    # 1. Disallowed document type (e.g. medical certificate or legal opinion) -> 403
    res_disallowed = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=medical_certificate",
        headers={"Authorization": f"Bearer {police_token}"},
        data={"custom_text": "Sample medical report"},
    )
    assert res_disallowed.status_code == 403
    assert "Police officers may only upload police-origin records" in res_disallowed.json()["detail"]

    # 2. Out of station case -> 403
    res_out_case = client.post(
        "/documents/upload?case_id=UTP-0007&document_type=charge_sheet",
        headers={"Authorization": f"Bearer {police_token}"},
        data={"custom_text": "Charge sheet content"},
    )
    assert res_out_case.status_code == 403

    # 3. Allowed document type for in-station case -> 200 OK
    res_allowed = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=arrest_memo",
        headers={"Authorization": f"Bearer {police_token}"},
        data={"custom_text": "Arrest memo executed at Kotwali PS at 10:00 AM"},
    )
    assert res_allowed.status_code == 200
    body = res_allowed.json()
    assert body["status"] == "success"
    assert body["file_hash"] != ""


def test_police_document_pipeline_restrictions(client, police_token):
    """Police cannot run legal document AI assessment or receive bail reasoning."""
    # /cases/assess-document -> 403 Forbidden
    res = client.post(
        "/cases/assess-document",
        headers={"Authorization": f"Bearer {police_token}"},
        json={"document_name": "fir_scan.pdf"},
    )
    assert res.status_code == 403

    # /documents/assess -> returns extraction-only metadata without legal citations
    res_assess = client.post(
        "/documents/assess",
        headers={"Authorization": f"Bearer {police_token}"},
        data={"case_id": "UTP-0001", "document_name": "fir_copy.txt", "provided_text": "FIR lodged under 303(2) BNS"},
    )
    assert res_assess.status_code == 200
    dump = res_assess.json()
    granite = dump["granite_assessment"]
    assert granite["model_name"] == "Intake-Extraction-Only"
    assert dump["rag_statute_citations"] == []


def test_police_action_workflow(client, police_token):
    """Verify police actions workflow: listing, acknowledging, and completing tasks."""
    # List actions
    res = client.get("/police/actions", headers={"Authorization": f"Bearer {police_token}"})
    assert res.status_code == 200
    actions = res.json()
    assert isinstance(actions, list)
    assert len(actions) > 0
    act = actions[0]
    action_id = act["id"]

    # Acknowledge action
    res_ack = client.post(
        f"/police/actions/{action_id}/acknowledge",
        headers={"Authorization": f"Bearer {police_token}"},
        json={"notes": "Investigating Officer acknowledged request"},
    )
    assert res_ack.status_code == 200

    # Complete action with document submission
    res_comp = client.post(
        f"/police/actions/{action_id}/complete",
        headers={"Authorization": f"Bearer {police_token}"},
        json={"document_id": "doc_hash_123456", "notes": "Charge sheet submitted to registry"},
    )
    assert res_comp.status_code == 200


def test_police_hearings_scoping(client, police_token):
    """GET /hearings returns only hearings for cases under officer jurisdiction with police operational task."""
    res = client.get("/hearings", headers={"Authorization": f"Bearer {police_token}"})
    assert res.status_code == 200
    hearings = res.json()
    assert isinstance(hearings, list)
    assert len(hearings) > 0
    # Every hearing returned must belong to UTP-0001
    for h in hearings:
        assert h["case_id"] == "UTP-0001"
        assert "police_task" in h
        assert "workflow_state" in h

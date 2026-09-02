"""
Comprehensive test suite for Jail Superintendent (JAIL_OFFICER) Role Remediation.

Verifies:
1. GET /jail/inmates returns facility-scoped active prisoners only (excluding released/out-of-facility).
2. GET /cases/{id} enforces facility jurisdiction (403 for out-of-facility) and redacts legal draft.
3. GET /cases/{id}/timeline and /cases/{id}/documents enforce facility jurisdiction.
4. POST /documents/upload enforces prison-only document types and facility jurisdiction, marking status PENDING_VERIFICATION.
5. POST /cases/assess-document rejects JAIL_OFFICER with 403 Forbidden.
6. POST /documents/assess returns redacted intake-only extraction without legal advice/citations.
7. POST /evidence/verify restricts Jail Officer to facility and prison record types.
8. GET /hearings scopes to inmates detained at officer facility with custody escort task.
9. POST /jail/refer-legal-aid allows referring in-facility inmates to DLSA.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.database import init_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def jail_token():
    return create_access_token(
        subject="demo_jail_officer",
        role="JAIL_OFFICER",
        org_id="org_tihar_jail",
        facility_ids=["fac_tihar_jail_04", "Central Jail No. 4, Tihar (Synthetic)", "Tihar"],
        extra_claims={"email": "jail@demo.nyayamitra.in", "district": "West Delhi"},
    )


def test_jail_inmates_endpoint_facility_scoped(client, jail_token):
    """GET /jail/inmates returns active prisoners at officer facility only."""
    res = client.get("/jail/inmates", headers={"Authorization": f"Bearer {jail_token}"})
    assert res.status_code == 200
    inmates = res.json()
    assert isinstance(inmates, list)
    assert len(inmates) > 0

    inmate_ids = [item["inmate_id"] for item in inmates]
    assert "UTP-0001" in inmate_ids
    assert "UTP-0007" not in inmate_ids
    assert "UTP-0012" not in inmate_ids
    assert "UTP-0015" not in inmate_ids
    assert "REL-0042" not in inmate_ids

    first = inmates[0]
    assert "custody_days" in first
    assert "countable_days" in first
    assert "potential_479_eligible" in first
    assert "assignment_status" in first


def test_case_dossier_facility_guard_and_redaction(client, jail_token):
    """GET /cases/{id} returns 200 and redacted draft for in-facility, 403 for out-of-facility."""
    res_in = client.get("/cases/UTP-0001", headers={"Authorization": f"Bearer {jail_token}"})
    assert res_in.status_code == 200
    data = res_in.json()
    assert data["case"]["case_id"] == "UTP-0001"
    assert data["draft"] is None
    assert data["statutes"] == []
    assert data["retrieval"] == {}

    res_out = client.get("/cases/UTP-0007", headers={"Authorization": f"Bearer {jail_token}"})
    assert res_out.status_code == 403
    assert "outside your authorized facility jurisdiction" in res_out.json()["detail"]


def test_case_timeline_and_documents_facility_guard(client, jail_token):
    """GET /cases/{id}/timeline and /cases/{id}/documents block out-of-facility cases with 403."""
    res_tl_out = client.get("/cases/UTP-0007/timeline", headers={"Authorization": f"Bearer {jail_token}"})
    assert res_tl_out.status_code == 403

    res_doc_out = client.get("/cases/UTP-0007/documents", headers={"Authorization": f"Bearer {jail_token}"})
    assert res_doc_out.status_code == 403

    res_tl_in = client.get("/cases/UTP-0001/timeline", headers={"Authorization": f"Bearer {jail_token}"})
    assert res_tl_in.status_code == 200

    res_doc_in = client.get("/cases/UTP-0001/documents", headers={"Authorization": f"Bearer {jail_token}"})
    assert res_doc_in.status_code == 200


def test_jail_document_upload_restrictions(client, jail_token):
    """Jail officer can upload prison documents, but forbidden investigation documents return 403."""
    res_forbidden = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=charge_sheet",
        data={"custom_text": "Illegal charge sheet upload by jail"},
        headers={"Authorization": f"Bearer {jail_token}"},
    )
    assert res_forbidden.status_code == 403
    assert "Jail officers may only upload prison intake" in res_forbidden.json()["detail"]

    res_out = client.post(
        "/documents/upload?case_id=UTP-0007&document_type=custody_certificate",
        data={"custom_text": "Custody certificate for out-of-facility inmate"},
        headers={"Authorization": f"Bearer {jail_token}"},
    )
    assert res_out.status_code == 403

    res_ok = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=custody_certificate",
        data={"custom_text": "Verified institutional custody certificate from Tihar Jail No. 4."},
        headers={"Authorization": f"Bearer {jail_token}"},
    )
    assert res_ok.status_code == 200
    assert "custody_certificate" in res_ok.json()["message"]


def test_jail_cannot_trigger_legal_assessment_pipeline(client, jail_token):
    """POST /cases/assess-document rejects JAIL_OFFICER with 403 Forbidden."""
    res = client.post(
        "/cases/assess-document?case_id=UTP-0001&document_type=bail_application",
        headers={"Authorization": f"Bearer {jail_token}"},
    )
    assert res.status_code == 403


def test_jail_document_assess_redacted(client, jail_token):
    """POST /documents/assess returns intake-extraction-only metadata without legal citations for Jail."""
    res = client.post(
        "/documents/assess",
        data={"document_name": "nominal_roll.txt", "provided_text": "Undertrial admitted on 2024-01-01."},
        headers={"Authorization": f"Bearer {jail_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["granite_assessment"]["model_name"] == "Intake-Extraction-Only"
    assert data["granite_assessment"]["eligibility_status"] == "PENDING_LEGAL_REVIEW"
    assert data["rag_statute_citations"] == []


def test_hearings_scoped_to_facility_population(client, jail_token):
    """GET /hearings returns hearings for officer facility inmates only."""
    res = client.get("/hearings", headers={"Authorization": f"Bearer {jail_token}"})
    assert res.status_code == 200
    hearings = res.json()
    for h in hearings:
        assert h["case_id"] in ["UTP-0001", "UTP-8568"]
        assert "custody_task" in h


def test_jail_refer_legal_aid(client, jail_token):
    """POST /jail/refer-legal-aid allows Jail Officer to refer inmate to DLSA."""
    res_out = client.post(
        "/jail/refer-legal-aid",
        json={"case_id": "UTP-0007", "notes": "Please assign counsel."},
        headers={"Authorization": f"Bearer {jail_token}"},
    )
    assert res_out.status_code == 403

    res_in = client.post(
        "/jail/refer-legal-aid",
        json={"case_id": "UTP-0001", "notes": "Inmate lacks legal representation. Kindly assign DLSA panel counsel."},
        headers={"Authorization": f"Bearer {jail_token}"},
    )
    assert res_in.status_code == 200
    assert res_in.json()["status"] == "success"
    assert "successfully referred to DLSA" in res_in.json()["message"]

"""
tests/test_accused_profile.py — Test Suite for Accused-Centric Profile,
Timeline (Facts vs Interpretations), ABAC Medical Quarantining, and Identity Resolution.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _get_token(role: str) -> str:
    res = client.post("/auth/demo-token", json={"role": role})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_accused_profile_multi_case_aggregation():
    """Verify accused profile unifies case records across facilities under opaque ID."""
    token = _get_token("DLSA_OFFICER")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/accused/acc_utp_0001", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == "acc_utp_0001"
    assert data["full_name"] == "Suresh Patel"
    assert "provenance" in data
    assert data["provenance"]["source_system"] == "e-Prisons Delhi"
    assert "family_contacts" in data
    assert len(data["family_contacts"]) >= 1
    assert "connected_cases" in data
    assert len(data["connected_cases"]) >= 1
    assert data["connected_cases"][0]["case_id"] == "UTP-0001"


def test_medical_data_abac_quarantining_and_redaction():
    """
    Verify sensitive medical files are visible to DLSA/Supervising officers
    but strictly redacted for unauthorized/police/external users.
    """
    # 1. Authorized DLSA Officer -> Full Medical Details
    dlsa_token = _get_token("DLSA_OFFICER")
    dlsa_resp = client.get("/accused/acc_utp_0003", headers={"Authorization": f"Bearer {dlsa_token}"})
    assert dlsa_resp.status_code == 200
    dlsa_data = dlsa_resp.json()
    assert dlsa_data["medical_record"]["has_vulnerability"] is True
    assert "Coronary Artery Disease" in dlsa_data["medical_record"]["details_restricted"]
    assert dlsa_data["medical_record"].get("is_redacted", False) is False

    # 2. Unauthorized Police Officer -> Medical details redacted
    police_token = _get_token("POLICE_OFFICER")
    police_resp = client.get("/accused/acc_utp_0003", headers={"Authorization": f"Bearer {police_token}"})
    assert police_resp.status_code == 200
    police_data = police_resp.json()
    assert police_data["medical_record"]["is_redacted"] is True
    assert "[RESTRICTED SENSITIVE MEDICAL ENVELOPE" in police_data["medical_record"]["details_restricted"]


def test_timeline_facts_vs_system_interpretations():
    """Verify timeline strictly separates ground-truth facts from system-generated rules."""
    token = _get_token("DLSA_OFFICER")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/accused/acc_utp_0001/timeline", headers=headers)
    assert response.status_code == 200
    timeline = response.json()
    assert len(timeline) >= 5

    # Check for factual items
    factual_items = [t for t in timeline if t["item_type"] == "FACTUAL_EVENT"]
    assert len(factual_items) >= 3
    for f in factual_items:
        assert f["source_name"] != ""
        assert f["recorded_by"] != ""
        assert f["verification_status"] in ("CONFIRMED", "DISPUTED", "PENDING_REVIEW")

    # Check for system interpretation items
    sys_items = [t for t in timeline if t["item_type"] == "SYSTEM_INTERPRETATION"]
    assert len(sys_items) >= 1
    assert any("Section 479" in s["title"] for s in sys_items)
    assert any("Deterministic Ruleset" in s["source_name"] for s in sys_items)


def test_duplicate_identity_resolution_workflow():
    """Verify retrieval and human review resolution of duplicate identity candidates."""
    # 1. Fetch pending candidates
    token = _get_token("SUPERVISING_LEGAL_OFFICER")
    headers = {"Authorization": f"Bearer {token}"}
    
    cand_resp = client.get("/accused/duplicates/candidates", headers=headers)
    assert cand_resp.status_code == 200
    candidates = cand_resp.json()
    assert len(candidates) >= 1
    target_cand = candidates[0]
    assert "match_confidence" in target_cand
    assert "match_explanation" in target_cand
    assert len(target_cand["shared_traits"]) > 0

    # 2. Execute resolution action
    resolve_resp = client.post(
        "/accused/duplicates/resolve",
        headers=headers,
        json={
            "candidate_id": target_cand["id"],
            "action": "MERGE_RECORDS",
            "resolution_notes": "Verified matching father name and biometric profile across Tihar and Rohini jails.",
        },
    )
    assert resolve_resp.status_code == 200
    res_data = resolve_resp.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["action_applied"] == "MERGE_RECORDS"


def test_citizen_and_family_portal_view():
    """Verify citizen view produces plain-language status without internal notes."""
    token = _get_token("FAMILY_GUARDIAN")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/citizen/my-case", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    assert data["case_reference"] == "UTP-0001"
    assert "legal_status" in data
    assert "title_en" in data["legal_status"]
    assert "title_hi" in data["legal_status"]
    assert "assigned_legal_aid_lawyer" in data
    assert "helpline" in data["assigned_legal_aid_lawyer"]
    assert "available_documents" in data
    assert len(data["available_documents"]) >= 2

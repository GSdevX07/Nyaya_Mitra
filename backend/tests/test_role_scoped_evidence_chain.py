"""
test_role_scoped_evidence_chain.py
==================================
Exhaustive verification of role-specific, least-privilege, and facility/jurisdiction-scoped
evidence chain projections across all 11 roles in Nyaya Mitra:

1. JAIL_OFFICER -> "Document Verification & Provenance", facility-scoped, truthful integrity.
2. POLICE_OFFICER -> "Police Record Provenance", police jurisdiction scoped.
3. DLSA_OFFICER -> "Evidence Chain & Legal Record History", full legal-aid context.
4. SUPERVISING_LEGAL_OFFICER -> "Full Evidence Chain & Supervisory Audit", supervisory review.
5. DEFENSE_ADVOCATE -> "Case Evidence & Document History", assigned cases only.
6. CONTROLLED_EXTERNAL_ADVOCATE -> "Authorized Document History", strictly explicitly shared only.
7. READ_ONLY_AUDITOR -> "Audit Evidence Chain", complete timestamps & actor roles (read-only).
8. GOV_ADMIN -> "Evidence & Compliance Overview", contextual BSA 63 oversight indicators.
9. PLATFORM_ADMIN -> "Technical Document Integrity", raw SHA-256 and vault protection.
10. ACCUSED_USER -> "Document Status", simple plain language for own case.
11. FAMILY_GUARDIAN -> "Case Document Status", high-level status for linked accused.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role

client = TestClient(app)


def _token(role: Role, user_id: str = "u_test", facility_ids: list = None, extra: dict = None) -> dict:
    claims = extra or {}
    tok = create_access_token(
        subject=user_id,
        role=role.value,
        org_id="org_dlsa_central",
        facility_ids=facility_ids or [],
        extra_claims=claims,
    )
    return {"Authorization": f"Bearer {tok}"}


DOC_ID = "DOC-UTP-0001-remand_order"


def test_jail_officer_with_valid_facility_gets_jail_projection():
    """Jail Officer with facility scope matching Central Jail sees Document Verification & Provenance."""
    headers = _token(
        Role.JAIL_OFFICER,
        facility_ids=["fac_tihar_jail_04", "Central Jail No. 4, Tihar (Synthetic)", "tihar"],
        extra={"facility_id": "fac_tihar_jail_04", "district": "West Delhi"}
    )
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_view"] == "JAIL_OFFICER"
    assert data["ui_label"] == "Document Verification & Provenance"
    assert "integrity_status" in data
    assert data["integrity_status"] in ("Record intact", "Integrity check pending")
    assert data["verification_status"] in ("Institutionally Verified", "Pending Verification")
    # Hidden fields must NOT be present
    assert "statutory_rule_grounding" not in data
    assert "legal_aid_actions" not in data
    assert "counsel_actions" not in data


def test_jail_officer_without_facility_scope_denied():
    """Jail Officer without facility scope is rejected with 403 Forbidden."""
    headers = _token(Role.JAIL_OFFICER, facility_ids=[], extra={"facility_id": ""})
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 403
    assert "facility scope" in resp.json()["detail"].lower()


def test_police_officer_in_district_gets_police_projection():
    """Police Officer in matching district gets Police Record Provenance."""
    headers = _token(Role.POLICE_OFFICER, extra={"district": "Central Delhi"})
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_view"] == "POLICE_OFFICER"
    assert data["ui_label"] == "Police Record Provenance"
    assert "police_station" in data
    assert data["integrity_status"] in ("Record intact", "Integrity check pending")
    assert data["verification_status"] in ("Institutionally Verified", "Pending Verification")
    # Internal strategy and statutory analysis hidden
    assert "statutory_rule_grounding" not in data
    assert "advocate_strategy" not in data


def test_dlsa_officer_gets_full_legal_aid_evidence_chain():
    """DLSA Officer gets Evidence Chain & Legal Record History with workflow impact."""
    headers = _token(Role.DLSA_OFFICER, extra={"district": "Central Delhi"})
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_view"] == "DLSA_OFFICER"
    assert data["ui_label"] == "Evidence Chain & Legal Record History"
    assert "statutory_assessment_impact" in data
    assert "legal_aid_actions" in data


def test_supervising_legal_officer_gets_supervisory_audit():
    """Supervising Legal Officer gets Full Evidence Chain & Supervisory Audit."""
    headers = _token(Role.SUPERVISING_LEGAL_OFFICER, extra={"district": "Central Delhi"})
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_view"] == "SUPERVISING_LEGAL_OFFICER"
    assert data["ui_label"] == "Full Evidence Chain & Supervisory Audit"
    assert "complete_audit_trail" in data
    assert data["can_authorize_filing"] is True


def test_defense_advocate_assigned_gets_case_evidence():
    """Defense Counsel assigned to case gets Case Evidence & Document History."""
    # UTP-0001 is assigned to demo_advocate or Adv. Rajesh Sharma
    headers = _token(
        Role.DEFENSE_ADVOCATE,
        user_id="demo_advocate",
        extra={"full_name": "Adv. Rajesh Sharma", "linked_case_id": "UTP-0001"}
    )
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_view"] == "DEFENSE_ADVOCATE"
    assert data["ui_label"] == "Case Evidence & Document History"
    assert data["evidence_integrity_status"] in ("Integrity Verified", "Record intact")
    assert "relevant_extracted_facts" in data


def test_defense_advocate_unassigned_denied():
    """Defense Counsel NOT assigned to the case gets 403 Forbidden."""
    headers = _token(
        Role.DEFENSE_ADVOCATE,
        user_id="other_lawyer",
        extra={"full_name": "Adv. Unassigned Lawyer", "linked_case_id": "UTP-9999"}
    )
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 403
    assert "assigned cases" in resp.json()["detail"].lower()


def test_external_advocate_unshared_denied():
    """Controlled External Advocate trying to view an unshared document gets 403 Forbidden."""
    headers = _token(Role.CONTROLLED_EXTERNAL_ADVOCATE, user_id="demo_ext_advocate")
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 403
    assert "explicitly shared" in resp.json()["detail"].lower()


def test_external_advocate_with_linked_case_still_denied_if_doc_not_shared():
    """Controlled External Advocate CANNOT bypass explicit document sharing via linked_case_id."""
    headers = _token(
        Role.CONTROLLED_EXTERNAL_ADVOCATE,
        user_id="demo_ext_advocate",
        extra={"linked_case_id": "UTP-0001"}
    )
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 403
    assert "explicitly shared" in resp.json()["detail"].lower()


def test_read_only_auditor_gets_audit_evidence_chain():
    """Read-Only Auditor gets full audit evidence chain with raw hash and actor timestamps."""
    headers = _token(Role.READ_ONLY_AUDITOR, user_id="demo_auditor")
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_view"] == "READ_ONLY_AUDITOR"
    assert data["ui_label"] == "Audit Evidence Chain"
    assert data["is_read_only"] is True
    assert "file_hash_sha256" in data


def test_government_admin_gets_compliance_overview():
    """Government Admin gets Evidence & Compliance Overview with contextual BSA Section 63 reference."""
    headers = _token(Role.GOV_ADMIN, user_id="demo_gov")
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_view"] == "GOV_ADMIN"
    assert data["ui_label"] == "Evidence & Compliance Overview"
    assert "compliance_indicators" in data
    assert data["compliance_indicators"]["electronic_record_legal_reference"] == "BSA Section 63 where applicable"


def test_platform_admin_gets_technical_integrity():
    """Platform Admin gets Technical Document Integrity with storage vault and sha256_hash."""
    headers = _token(Role.PLATFORM_ADMIN, user_id="demo_admin")
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_view"] == "PLATFORM_ADMIN"
    assert data["ui_label"] == "Technical Document Integrity"
    assert "storage_vault" in data
    assert "sha256_hash" in data
    assert data["consequential_legal_authority"] is False


def test_accused_user_linked_gets_document_status():
    """Accused User linked to UTP-0001 gets clean Document Status without hashes."""
    headers = _token(Role.ACCUSED_USER, user_id="demo_accused", extra={"linked_case_id": "UTP-0001"})
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_view"] == "ACCUSED_USER"
    assert data["ui_label"] == "Document Status"
    assert "simple_status" in data
    # No technical details
    assert "sha256_hash" not in data
    assert "statutory_rule_grounding" not in data


def test_accused_user_unlinked_denied():
    """Accused User attempting to access another case gets 403 Forbidden."""
    headers = _token(Role.ACCUSED_USER, user_id="demo_accused_other", extra={"linked_case_id": "UTP-0002"})
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 403


def test_family_guardian_linked_gets_case_document_status():
    """Family Guardian linked to UTP-0001 gets Case Document Status."""
    headers = _token(Role.FAMILY_GUARDIAN, user_id="demo_family", extra={"linked_case_id": "UTP-0001"})
    resp = client.get(f"/documents/{DOC_ID}/evidence-chain", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_view"] == "FAMILY_GUARDIAN"
    assert data["ui_label"] == "Case Document Status"
    assert "high_level_status" in data

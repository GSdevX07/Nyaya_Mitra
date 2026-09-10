"""
test_stage19_advocate_role_hardening.py - Comprehensive Role Hardening Suite for DEFENSE_ADVOCATE.
===================================================================================================
Rigorous verification of DEFENSE_ADVOCATE role capabilities and security boundaries:
1. Scoped access: assigned cases only; unassigned, cross-org, and cross-district are blocked (403).
2. Grounded draft generation with exact canonical case facts snapshot, retrieved authorities, and provenance.
3. Anti-hallucination & missing fields: [MISSING: FIELD] markers and blocking issues.
4. Pre-approval readiness gating: blocks approval when missing facts, uncited citations, or missing evidence exist.
5. Formal human approval & permanent immutability locking (is_immutable = 1).
6. Revision workflow allocating Version N+1, preserving historical versions immutably.
7. Dual-pane editing, commenting, and rejection workflows.
8. Line-level version diff computation against machine originals and previous versions.
9. Segregated export: external court copies omit internal audit notes; internal copies authorized.
10. Anti-automatic filing: package preparation manifest does not file; recording filing requires receipt/CNR.

Strictly NO emojis in code, comments, test names, docstrings, or assertions.
"""

import pytest
import datetime
import json
from fastapi.testclient import TestClient

from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.database import (
    init_db,
    get_case,
    get_db_connection,
    _MEMORY_CASES,
    store_legal_document_draft,
    get_legal_document_draft,
    list_legal_document_drafts_for_case,
)
from app.models.schemas import CaseRecord, CaseState
from app.services.document_templates import seed_default_templates

client = TestClient(app)


def _make_token(
    user_id: str,
    role: Role,
    org_id: str = "org_dlsa_central",
    district: str = "Central Delhi",
    linked_case_id: str = None,
    authorized_district_ids: list = None,
    full_name: str = "Adv. Rajesh Sharma",
) -> str:
    claims = {
        "full_name": full_name,
        "district": district,
        "email": f"{user_id}@nyayamitra.in",
        "authorized_district_ids": authorized_district_ids or [district],
    }
    if linked_case_id:
        claims["linked_case_id"] = linked_case_id
    return create_access_token(
        subject=user_id,
        role=role.value,
        org_id=org_id,
        facility_ids=["fac_central_01"],
        extra_claims=claims,
    )


def _auth_header(
    user_id: str,
    role: Role,
    org_id: str = "org_dlsa_central",
    district: str = "Central Delhi",
    linked_case_id: str = None,
    authorized_district_ids: list = None,
    full_name: str = "Adv. Rajesh Sharma",
) -> dict:
    tok = _make_token(
        user_id=user_id,
        role=role,
        org_id=org_id,
        district=district,
        linked_case_id=linked_case_id,
        authorized_district_ids=authorized_district_ids,
        full_name=full_name,
    )
    return {"Authorization": f"Bearer {tok}"}


def _insert_test_case(case_dict: dict):
    defaults = {
        "prisoner_category": "UNDERTRIAL",
        "legal_code": "BNS_2023",
        "offense_sections": ["Section 303"],
        "arrest_date": "2024-03-01",
        "custody_days": 420,
        "max_sentence_days_for_offense": 730,
        "punishable_by_death_or_life": False,
        "multiple_active_cases": False,
        "required_docs": ["remand_order", "charge_sheet", "custody_certificate"],
        "present_docs": ["remand_order", "charge_sheet", "custody_certificate"],
        "urgency_flags": {"age": 32, "health_flag": False, "repeat_offender": False},
        "jail_location": "Central Jail Tihar",
        "district": "Central Delhi",
        "state": "Delhi",
        "court_name": "Court of Sessions Judge at Delhi",
        "parent_name": "Harbans Singh",
        "assignment_status": "ASSIGNED",
        "data_source_status": "DEMO_SYNTHETIC",
        "status": "HUMAN_REVIEW",
        "evidence_verified": True,
        "organization_id": "org_dlsa_central",
    }
    full_dict = {**defaults, **case_dict}
    case_rec = CaseRecord(**full_dict)
    _MEMORY_CASES[case_rec.case_id] = case_rec
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO cases (case_id, data, status, assignment_status, assigned_lawyer_id) VALUES (?, ?, ?, ?, ?)",
        (
            case_rec.case_id,
            json.dumps(case_rec.model_dump()),
            case_rec.status.value if hasattr(case_rec.status, "value") else str(case_rec.status),
            case_rec.assignment_status,
            getattr(case_rec, "assigned_lawyer_id", None),
        ),
    )
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def setup_advocate_hardening_db():
    init_db()
    seed_default_templates()

    # Seed Canonical Assigned Case
    _insert_test_case({
        "case_id": "UTP-ADV-001",
        "name": "Vikram Singh",
        "accused_name": "Vikram Singh",
        "fir_number": "FIR-442/2024",
        "police_station": "Kotwali Police Station",
        "offense_sections": ["Section 303", "Section 305"],
        "custody_days": 420,
        "max_sentence_days_for_offense": 730,
        "district": "Central Delhi",
        "court_name": "Court of Sessions Judge at Delhi",
        "parent_name": "Harbans Singh",
        "status": "HUMAN_REVIEW",
        "assignment_status": "ASSIGNED",
        "assigned_lawyer": "Adv. Rajesh Sharma",
        "assigned_lawyer_id": "adv_rajesh_01",
        "organization_id": "org_dlsa_central",
        "present_docs": ["remand_order", "charge_sheet", "custody_certificate"],
        "evidence_verified": True,
    })

    # Seed Unassigned Case in same org
    _insert_test_case({
        "case_id": "UTP-ADV-UNASSIGNED",
        "name": "Sunil Dutt",
        "accused_name": "Sunil Dutt",
        "fir_number": "FIR-101/2024",
        "police_station": "Daryaganj Police Station",
        "status": "LEGAL_AID_REQUIRED",
        "assignment_status": "UNASSIGNED",
        "assigned_lawyer": None,
        "assigned_lawyer_id": None,
        "organization_id": "org_dlsa_central",
        "present_docs": ["remand_order"],
    })

    # Seed Cross-Org Case
    _insert_test_case({
        "case_id": "UTP-ADV-CROSS-ORG",
        "name": "Karan Verma",
        "accused_name": "Karan Verma",
        "district": "Hyderabad",
        "state": "Telangana",
        "court_name": "Metropolitan Sessions Court",
        "status": "HUMAN_REVIEW",
        "assignment_status": "ASSIGNED",
        "assigned_lawyer": "Adv. Suresh Reddy",
        "assigned_lawyer_id": "adv_suresh_hyd",
        "organization_id": "org_dlsa_hyd",
        "present_docs": ["remand_order", "charge_sheet", "custody_certificate"],
    })

    # Seed Cross-District Case within same Org
    _insert_test_case({
        "case_id": "UTP-ADV-CROSS-DIST",
        "name": "Rohit Sharma",
        "accused_name": "Rohit Sharma",
        "district": "North Delhi",
        "status": "HUMAN_REVIEW",
        "assignment_status": "ASSIGNED",
        "assigned_lawyer": "Adv. Anita Roy",
        "assigned_lawyer_id": "adv_anita_north",
        "organization_id": "org_dlsa_central",
        "present_docs": ["remand_order", "custody_certificate"],
    })


# ==============================================================================
# SCENARIO 1: Unassigned Advocate Denied Access
# ==============================================================================
def test_scenario_01_unassigned_advocate_cannot_access_case_drafts():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    # Attempting to access unassigned case drafts
    res = client.get("/api/documents/drafts/case/UTP-ADV-UNASSIGNED", headers=adv_headers)
    assert res.status_code == 403
    assert "not assigned to you" in res.json()["detail"].lower()

    # Attempting to generate draft on unassigned case
    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-UNASSIGNED", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    assert gen_res.status_code == 403


# ==============================================================================
# SCENARIO 2: Cross-Organization Access Denied
# ==============================================================================
def test_scenario_02_cross_organization_advocate_denied_access():
    adv_headers = _auth_header(
        user_id="adv_rajesh_01",
        role=Role.DEFENSE_ADVOCATE,
        org_id="org_dlsa_central",
    )

    # Attempting to access case belonging to org_dlsa_hyd
    res = client.get("/api/documents/drafts/case/UTP-ADV-CROSS-ORG", headers=adv_headers)
    assert res.status_code == 403
    assert "outside your organization" in res.json()["detail"].lower()


# ==============================================================================
# SCENARIO 3: Cross-District Access Denied
# ==============================================================================
def test_scenario_03_cross_district_advocate_denied_access():
    adv_headers = _auth_header(
        user_id="adv_rajesh_01",
        role=Role.DEFENSE_ADVOCATE,
        district="Central Delhi",
        authorized_district_ids=["Central Delhi"],
    )

    # Attempting to access case in North Delhi
    res = client.get("/api/documents/drafts/case/UTP-ADV-CROSS-DIST", headers=adv_headers)
    assert res.status_code == 403
    assert "outside your authorized district jurisdiction" in res.json()["detail"].lower()


# ==============================================================================
# SCENARIO 4: Assigned Advocate Can Generate Grounded Draft
# ==============================================================================
def test_scenario_04_assigned_advocate_can_generate_grounded_draft():
    adv_headers = _auth_header(
        user_id="adv_rajesh_01",
        role=Role.DEFENSE_ADVOCATE,
        org_id="org_dlsa_central",
        district="Central Delhi",
    )

    res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["case_id"] == "UTP-ADV-001"
    assert data["status"] == "DRAFT"
    assert data["version_number"] == 1
    assert data["is_immutable"] is False
    assert "VIKRAM SINGH" in data["content_text"]
    assert "FIR-442/2024" in data["content_text"]
    assert "Section 479" in data["content_text"]


# ==============================================================================
# SCENARIO 5: Draft Generation Preserves Full AI Provenance Record
# ==============================================================================
def test_scenario_05_draft_generation_preserves_original_ai_record_and_provenance():
    adv_headers = _auth_header(
        user_id="adv_rajesh_01",
        role=Role.DEFENSE_ADVOCATE,
        org_id="org_dlsa_central",
        district="Central Delhi",
    )

    res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    assert res.status_code == 201
    data = res.json()

    # Verifying stored provenance attributes
    assert "original_ai_text" in data and len(data["original_ai_text"]) > 100
    assert data["template_id"] == "tmpl_bnss_479_bail_v1"
    assert data["template_version"] >= 1
    assert "prompt_version" in data
    assert "ai_model_name" in data
    assert "exact_case_facts" in data
    assert data["exact_case_facts"]["fir_number"] == "FIR-442/2024"
    assert "source_documents" in data
    assert any(d["document_type"] == "remand_order" for d in data["source_documents"])


# ==============================================================================
# SCENARIO 6: Missing Facts Generate Tokens and Block Approval
# ==============================================================================
def test_scenario_06_missing_facts_generate_missing_tokens_and_block_approval():
    _insert_test_case({
        "case_id": "UTP-ADV-MISSING",
        "name": "Ramesh Kumar",
        "accused_name": "Ramesh Kumar",
        "fir_number": "",
        "police_station": "Daryaganj Police Station",
        "parent_name": "",
        "status": "HUMAN_REVIEW",
        "assignment_status": "ASSIGNED",
        "assigned_lawyer": "Adv. Rajesh Sharma",
        "assigned_lawyer_id": "adv_rajesh_01",
        "organization_id": "org_dlsa_central",
        "present_docs": ["remand_order", "charge_sheet", "custody_certificate"],
    })

    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-MISSING", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    assert gen_res.status_code == 201
    draft = gen_res.json()
    draft_id = draft["draft_id"]

    # Verify missing token rendered
    assert "[MISSING: FIR_NUMBER]" in draft["content_text"]

    # Attempting to approve while missing tokens remain
    appr_res = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Attempting sign-off with missing tokens"},
        headers=adv_headers,
    )
    assert appr_res.status_code == 400
    assert appr_res.json()["detail"]["total_blocking_issues"] >= 1


# ==============================================================================
# SCENARIO 7: Unsupported Factual Claims Block Advocate Approval
# ==============================================================================
def test_scenario_07_unsupported_factual_claims_block_advocate_approval():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]

    # Edit draft removing accused name entirely
    bad_content = gen_res.json()["content_text"].replace("VIKRAM SINGH", "HALLUCINATED_NAME_NOT_ON_RECORD")
    edit_res = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": bad_content},
        headers=adv_headers,
    )
    assert edit_res.status_code == 200

    # Attempting to approve with unsupported factual claim
    appr_res = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Sign-off attempt with hallucinated name"},
        headers=adv_headers,
    )
    assert appr_res.status_code == 400
    detail = appr_res.json()["detail"]
    assert any(b["category"] == "UNSUPPORTED_FACTUAL_CLAIM" for b in detail["blocking_issues"])


# ==============================================================================
# SCENARIO 8: Uncited Legal Assertions Block Advocate Approval
# ==============================================================================
def test_scenario_08_uncited_legal_assertions_block_advocate_approval():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]

    # Inject fabricated section citation (e.g., Section 9999 BNSS)
    bad_content = gen_res.json()["content_text"] + "\nGround 5: As per Section 9999 of the statute, bail is mandatory.\n"
    edit_res = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": bad_content},
        headers=adv_headers,
    )
    assert edit_res.status_code == 200

    # Attempting to approve with uncited statutory reference
    appr_res = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Sign-off attempt with fake section citation"},
        headers=adv_headers,
    )
    assert appr_res.status_code == 400
    detail = appr_res.json()["detail"]
    assert any(b["category"] == "UNCITED_LEGAL_ASSERTION" for b in detail["blocking_issues"])


# ==============================================================================
# SCENARIO 9: Missing Required Evidence Blocks Advocate Approval
# ==============================================================================
def test_scenario_09_missing_required_evidence_blocks_advocate_approval():
    _insert_test_case({
        "case_id": "UTP-ADV-NO-REMAND",
        "name": "Deepak Joshi",
        "accused_name": "Deepak Joshi",
        "status": "HUMAN_REVIEW",
        "assignment_status": "ASSIGNED",
        "assigned_lawyer": "Adv. Rajesh Sharma",
        "assigned_lawyer_id": "adv_rajesh_01",
        "organization_id": "org_dlsa_central",
        "present_docs": ["charge_sheet"],  # remand_order is missing!
        "evidence_verified": False,
    })

    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-NO-REMAND", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]

    # Attempting to approve without verified remand order
    appr_res = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Approval attempt without remand order"},
        headers=adv_headers,
    )
    assert appr_res.status_code == 400
    detail = appr_res.json()["detail"]
    assert any(b["category"] == "MISSING_PREREQUISITE_EVIDENCE" for b in detail["blocking_issues"])


# ==============================================================================
# SCENARIO 10: Cleared Readiness Allows Advocate Formal Approval
# ==============================================================================
def test_scenario_10_cleared_readiness_allows_advocate_formal_approval():
    adv_headers = _auth_header(
        user_id="adv_rajesh_01",
        role=Role.DEFENSE_ADVOCATE,
        full_name="Adv. Rajesh Sharma",
    )

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]

    # Check readiness endpoint
    readiness_res = client.get(f"/api/documents/drafts/{draft_id}/readiness", headers=adv_headers)
    assert readiness_res.status_code == 200
    assert readiness_res.json()["can_approve"] is True

    # Execute formal legal approval
    appr_res = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Verified all case records and Section 479 calculation. Approved."},
        headers=adv_headers,
    )
    assert appr_res.status_code == 200
    data = appr_res.json()
    assert data["status"] == "APPROVED"
    assert data["is_immutable"] is True
    assert "Adv. Rajesh Sharma" in data["approved_by"]
    assert data["approved_at"] is not None


# ==============================================================================
# SCENARIO 11: Approved Document Is Permanently Immutable
# ==============================================================================
def test_scenario_11_approved_document_is_permanently_immutable():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]

    # Approve draft
    client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Formal sign-off"},
        headers=adv_headers,
    )

    # Attempt to directly modify approved document
    edit_res = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Unauthorized modification after approval"},
        headers=adv_headers,
    )
    assert edit_res.status_code == 403
    assert "permanently immutable" in edit_res.json()["detail"].lower()


# ==============================================================================
# SCENARIO 12: Assigned Advocate Can Edit Working Draft Before Approval
# ==============================================================================
def test_scenario_12_assigned_advocate_can_edit_working_draft_before_approval():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]
    orig_text = gen_res.json()["content_text"]

    # Add custom legal argument
    custom_text = orig_text + "\n5. Additional Ground: The applicant has clean antecedents and is the sole breadwinner.\n"
    edit_res = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": custom_text},
        headers=adv_headers,
    )
    assert edit_res.status_code == 200
    assert "sole breadwinner" in edit_res.json()["content_text"]


# ==============================================================================
# SCENARIO 13: Assigned Advocate Can Add Threaded Comments
# ==============================================================================
def test_scenario_13_assigned_advocate_can_add_threaded_comments():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]

    comment_res = client.post(
        f"/api/documents/drafts/{draft_id}/comments",
        json={"comment": "Cross-verified custody certificate with Tihar Jail record."},
        headers=adv_headers,
    )
    assert comment_res.status_code == 200
    comments = comment_res.json().get("reviewer_comments", [])
    assert len(comments) >= 1
    assert "Tihar Jail record" in comments[0]["comment"]


# ==============================================================================
# SCENARIO 14: Assigned Advocate Can Reject Draft with Mandatory Reason
# ==============================================================================
def test_scenario_14_assigned_advocate_can_reject_draft_with_mandatory_reason():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]

    # Reject with empty reason fails
    empty_rej = client.post(
        f"/api/documents/drafts/{draft_id}/reject",
        json={"reason": "   "},
        headers=adv_headers,
    )
    assert empty_rej.status_code == 400

    # Reject with valid reason
    valid_rej = client.post(
        f"/api/documents/drafts/{draft_id}/reject",
        json={"reason": "Charge sheet charges need re-verification against e-Courts."},
        headers=adv_headers,
    )
    assert valid_rej.status_code == 200
    assert valid_rej.json()["status"] == "REJECTED"


# ==============================================================================
# SCENARIO 15: Revision Workflow Creates Version N+1 Preserving History
# ==============================================================================
def test_scenario_15_revision_workflow_creates_version_n_plus_1_preserving_history():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    # 1. Generate Version 1 and approve it
    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_v1_id = gen_res.json()["draft_id"]
    client.post(
        f"/api/documents/drafts/{draft_v1_id}/approve",
        json={"comment": "Approved Version 1"},
        headers=adv_headers,
    )

    # 2. Initiate Revision
    rev_res = client.post(
        f"/api/documents/drafts/{draft_v1_id}/revise",
        headers=adv_headers,
    )
    assert rev_res.status_code == 201
    draft_v2 = rev_res.json()
    assert draft_v2["version_number"] == 2
    assert draft_v2["status"] == "DRAFT"
    assert draft_v2["is_immutable"] is False
    assert draft_v2["approved_by"] is None

    # 3. Verify Version 1 remains intact in database
    v1_stored = get_legal_document_draft(draft_v1_id)
    assert v1_stored["version_number"] == 1
    assert v1_stored["status"] == "APPROVED"
    assert v1_stored["is_immutable"] is True


# ==============================================================================
# SCENARIO 16: Draft Diff Computes Line-by-Line Comparison
# ==============================================================================
def test_scenario_16_draft_diff_computes_line_by_line_comparison():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]
    orig_text = gen_res.json()["content_text"]

    # Modify draft
    new_text = orig_text + "\nADDED LINE: Submitting surety undertaking bond.\n"
    client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": new_text},
        headers=adv_headers,
    )

    # Fetch diff against machine original
    diff_res = client.get(f"/api/documents/drafts/{draft_id}/diff?compare_with=original", headers=adv_headers)
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert diff_data["additions"] >= 1
    assert any(line["type"] == "ADDED" and "surety undertaking" in line["text"] for line in diff_data["diff_lines"])


# ==============================================================================
# SCENARIO 17: External Export Strictly Omits Privileged Internal Notes
# ==============================================================================
def test_scenario_17_external_export_omits_privileged_internal_notes():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]

    # Add confidential comment
    client.post(
        f"/api/documents/drafts/{draft_id}/comments",
        json={"comment": "CONFIDENTIAL_STRATEGY: Focus on prolonged trial delay."},
        headers=adv_headers,
    )

    # Export external court document
    exp_res = client.get(f"/api/documents/drafts/{draft_id}/export?include_internal_notes=false", headers=adv_headers)
    assert exp_res.status_code == 200
    payload = exp_res.json()
    assert payload["export_type"] == "EXTERNAL_COURT"
    assert payload["includes_internal_notes"] is False
    assert "CONFIDENTIAL_STRATEGY" not in payload["exported_text"]


# ==============================================================================
# SCENARIO 18: Internal Notes Export Permitted for Assigned Advocate
# ==============================================================================
def test_scenario_18_internal_notes_export_permitted_for_assigned_advocate():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]

    # Add comment
    client.post(
        f"/api/documents/drafts/{draft_id}/comments",
        json={"comment": "CONFIDENTIAL_STRATEGY_NOTES"},
        headers=adv_headers,
    )

    # Internal export request with permission
    exp_res = client.get(f"/api/documents/drafts/{draft_id}/export?include_internal_notes=true", headers=adv_headers)
    assert exp_res.status_code == 200
    payload = exp_res.json()
    assert payload["export_type"] == "INTERNAL_CERTIFIED"
    assert payload["includes_internal_notes"] is True
    assert "CONFIDENTIAL_STRATEGY_NOTES" in payload["exported_text"]


# ==============================================================================
# SCENARIO 19: Submission Package Requires Approved Draft and Does Not Auto-File
# ==============================================================================
def test_scenario_19_submission_package_requires_approved_draft_and_does_not_auto_file():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]

    # 1. Packaging unapproved draft fails
    unappr_pkg = client.post(
        f"/api/documents/drafts/{draft_id}/package",
        json={"exhibits": ["Remand Order", "Custody Certificate"]},
        headers=adv_headers,
    )
    assert unappr_pkg.status_code == 400
    assert "must be formally approved before packaging" in unappr_pkg.json()["detail"].lower()

    # 2. Approve draft
    client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Approved for package creation"},
        headers=adv_headers,
    )

    # 3. Packaging approved draft succeeds but does NOT automatically file
    pkg_res = client.post(
        f"/api/documents/drafts/{draft_id}/package",
        json={"exhibits": ["Remand Order", "Custody Certificate"]},
        headers=adv_headers,
    )
    assert pkg_res.status_code == 200
    pkg_data = pkg_res.json()
    assert pkg_data["is_automatically_filed"] is False
    assert pkg_data["filing_status"] == "PACKAGE_PREPARED_AWAITING_HUMAN_FILING"

    # Status in database is PACKAGE_PREPARED, NOT FILED
    draft_stored = get_legal_document_draft(draft_id)
    assert draft_stored["status"] == "PACKAGE_PREPARED"


# ==============================================================================
# SCENARIO 20: Recording Court Filing Requires Verified Reference
# ==============================================================================
def test_scenario_20_recording_court_filing_requires_verified_reference_and_transitions_matter():
    adv_headers = _auth_header(user_id="adv_rajesh_01", role=Role.DEFENSE_ADVOCATE)

    # 1. Generate & Approve Draft
    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-ADV-001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=adv_headers,
    )
    draft_id = gen_res.json()["draft_id"]
    client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Approved for filing"},
        headers=adv_headers,
    )

    # 2. Record filing with empty reference fails
    bad_filing = client.post(
        f"/api/documents/drafts/{draft_id}/record-filing",
        json={"filing_reference": "   ", "court_name": "Sessions Court"},
        headers=adv_headers,
    )
    assert bad_filing.status_code == 400

    # 3. Record filing with valid court receipt / CNR reference
    filing_res = client.post(
        f"/api/documents/drafts/{draft_id}/record-filing",
        json={
            "filing_reference": "CNR-DLCT01-00442-2024",
            "filing_date": "2024-08-15",
            "court_name": "Court of Sessions Judge at Delhi",
        },
        headers=adv_headers,
    )
    assert filing_res.status_code == 200
    f_data = filing_res.json()
    assert f_data["status"] == "FILED"
    assert f_data["external_filing_reference"] == "CNR-DLCT01-00442-2024"
    assert f_data["external_filing_date"] == "2024-08-15"

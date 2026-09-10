"""
test_stage19_dlsa_role_hardening.py - Security & RBAC Test Suite for DLSA Role Hardening.
========================================================================================
18 automated test scenarios verifying Stage 19 DLSA role hardening:
1. DLSA A cannot access District B case.
2. DLSA A cannot access Organization B case.
3. DLSA cannot edit legal pleading by default.
4. DLSA cannot approve document by default.
5. DLSA cannot package document by default.
6. DLSA cannot record filing by default.
7. DLSA cannot automatically file.
8. DLSA cannot mark source document VERIFIED unless authorized.
9. DLSA cannot modify immutable approved document.
10. DLSA cannot access unrelated case outside district scope.
11. DLSA can assign eligible counsel only when workflow permits.
12. DLSA can request document preparation (creates requisition and task).
13. Valid delegation enables only the delegated capability.
14. Expired delegation disables capability.
15. Revoked delegation disables capability immediately.
16. Delegation cannot cross organization scope.
17. Delegation cannot cross document-type scope.
18. Frontend and backend capability state must match.

Strictly NO emojis in code, comments, or assertions.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import (
    init_db,
    get_case,
    get_db_connection,
    _MEMORY_CASES,
    store_institutional_delegation,
    get_institutional_delegation,
    store_document_preparation_requisition,
    get_document_preparation_requisition,
    get_legal_document_draft,
    update_case_status,
)
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.models.schemas import CaseRecord, CaseState, DataSourceStatus
from app.services.document_templates import seed_default_templates

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_workspace():
    init_db()
    seed_default_templates()


def get_token_headers(
    role: str,
    user_id: str,
    org_id: str = "org_dlsa_central",
    district: str = "Central Delhi",
) -> dict:
    token = create_access_token(
        subject=user_id,
        role=role,
        org_id=org_id,
        extra_claims={"district": district, "authorized_district_ids": [district]},
    )
    return {"Authorization": f"Bearer {token}"}


def _insert_test_case(case_dict: dict):
    """Helper to insert a test case into SQLite and _MEMORY_CASES with all required fields."""
    defaults = {
        "prisoner_category": "UNDERTRIAL",
        "legal_code": "BNS_2023",
        "offense_sections": ["BNS 115(2)"],
        "arrest_date": "2025-01-10",
        "custody_days": 180,
        "max_sentence_days_for_offense": 365,
        "punishable_by_death_or_life": False,
        "multiple_active_cases": False,
        "required_docs": ["remand_order", "charge_sheet"],
        "present_docs": ["remand_order", "charge_sheet"],
        "urgency_flags": {"age": 28, "health_flag": False, "repeat_offender": False},
        "jail_location": "Central Jail No. 4, Tihar (Synthetic)",
        "assignment_status": "AVAILABLE",
        "data_source_status": "DEMO_SYNTHETIC",
        "status": "LEGAL_AID_REQUIRED",
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
            case_rec.model_dump_json(),
            case_rec.status.value,
            case_rec.assignment_status,
            case_rec.assigned_lawyer_id,
        ),
    )
    conn.commit()
    conn.close()
    return case_rec


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 1: DLSA A cannot access District B case
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_01_dlsa_a_cannot_access_district_b_case():
    """DLSA Officer in Central Delhi cannot assign counsel or requisition for South Delhi case."""
    headers_central = get_token_headers(
        Role.DLSA_OFFICER.value,
        "demo_dlsa_officer",
        org_id="org_dlsa_central",
        district="Central Delhi",
    )

    # UTP-0007 is located in South Delhi
    case = get_case("UTP-0007")
    assert case is not None
    assert case.district == "South Delhi"

    # 1. Counsel assignment must be blocked with 403 Forbidden
    res_assign = client.post(
        "/cases/UTP-0007/assign-counsel",
        json={"lawyer_id": "demo_advocate", "lawyer_name": "Adv. Rajesh Sharma"},
        headers=headers_central,
    )
    assert res_assign.status_code == 403
    assert "district" in res_assign.json()["detail"].lower()

    # 2. Document preparation requisition must be blocked with 403 Forbidden
    res_req = client.post(
        "/api/documents/drafts/request-preparation",
        json={
            "case_id": "UTP-0007",
            "template_id": "tmpl_bnss_479_bail_v1",
            "urgency": "URGENT",
            "reason": "Out-of-district coordination attempt",
        },
        headers=headers_central,
    )
    assert res_req.status_code == 403
    assert "district" in res_req.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 2: DLSA A cannot access Organization B case
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_02_dlsa_a_cannot_access_organization_b_case():
    """DLSA Officer in org_dlsa_central cannot coordinate on org_dlsa_east case."""
    headers_central = get_token_headers(
        Role.DLSA_OFFICER.value,
        "demo_dlsa_officer",
        org_id="org_dlsa_central",
        district="Central Delhi",
    )

    # Insert a case belonging to a different tenant organization
    _insert_test_case({
        "case_id": "UTP-FOREIGN-01",
        "name": "Foreign Tenant Inmate",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_east",
        "status": CaseState.LEGAL_AID_REQUIRED,
        "jail_location": "Tihar Jail No. 4",
        "custody_days": 180,
    })

    res_req = client.post(
        "/api/documents/drafts/request-preparation",
        json={
            "case_id": "UTP-FOREIGN-01",
            "template_id": "tmpl_bnss_479_bail_v1",
            "urgency": "ROUTINE",
            "reason": "Tenant crossing attempt",
        },
        headers=headers_central,
    )
    assert res_req.status_code == 403
    assert "organization" in res_req.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 3: DLSA cannot edit legal pleading by default
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_03_dlsa_cannot_edit_legal_pleading_by_default():
    """DLSA Officer cannot edit legal pleading text without an active delegation."""
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, "demo_advocate")
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_officer")

    # Generate draft as assigned advocate
    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    assert res_gen.status_code == 201
    draft_id = res_gen.json()["draft_id"]

    # DLSA attempts to edit draft text
    res_edit = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Unauthorized legal text revision by DLSA Officer."},
        headers=headers_dlsa,
    )
    assert res_edit.status_code == 403
    assert "delegation" in res_edit.json()["detail"].lower() or "restricted" in res_edit.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 4: DLSA cannot approve document by default
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_04_dlsa_cannot_approve_document_by_default():
    """DLSA Officer cannot give formal lawyer legal approval on court documents."""
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, "demo_advocate")
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_officer")

    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = res_gen.json()["draft_id"]

    res_appr = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "DLSA Officer approving draft"},
        headers=headers_dlsa,
    )
    assert res_appr.status_code == 403
    assert "approval is restricted" in res_appr.json()["detail"].lower() or "not authorized" in res_appr.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 5: DLSA cannot package document by default
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_05_dlsa_cannot_package_document_by_default():
    """DLSA Officer cannot prepare court submission package manifests."""
    headers_supervisor = get_token_headers(Role.SUPERVISING_LEGAL_OFFICER.value, "demo_supervising")
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_officer")

    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_supervisor,
    )
    draft_id = res_gen.json()["draft_id"]

    res_pkg = client.post(
        f"/api/documents/drafts/{draft_id}/package",
        json={"included_annexures": ["Custody Certificate"]},
        headers=headers_dlsa,
    )
    assert res_pkg.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 6: DLSA cannot record filing by default
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_06_dlsa_cannot_record_filing_by_default():
    """DLSA Officer cannot record external court filing references."""
    headers_supervisor = get_token_headers(Role.SUPERVISING_LEGAL_OFFICER.value, "demo_supervising")
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_officer")

    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_supervisor,
    )
    draft_id = res_gen.json()["draft_id"]

    res_filing = client.post(
        f"/api/documents/drafts/{draft_id}/record-filing",
        json={"filing_reference": "CNR-DLCT01-002934-2026"},
        headers=headers_dlsa,
    )
    assert res_filing.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 7: DLSA cannot automatically file
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_07_dlsa_cannot_automatically_file():
    """Verifies that platform policy prevents automated filing on draft lifecycle events."""
    headers_supervisor = get_token_headers(Role.SUPERVISING_LEGAL_OFFICER.value, "demo_supervising")
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_officer")

    # 1. DLSA dispatches requisition
    res_req = client.post(
        "/api/documents/drafts/request-preparation",
        json={
            "case_id": "UTP-0001",
            "template_id": "tmpl_bnss_479_bail_v1",
            "urgency": "URGENT",
            "reason": "Statutory eligibility",
        },
        headers=headers_dlsa,
    )
    assert res_req.status_code in (200, 201)

    # 2. Draft is generated and approved by supervisor
    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_supervisor,
    )
    draft_id = res_gen.json()["draft_id"]

    res_appr = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Approved by supervisor"},
        headers=headers_supervisor,
    )
    assert res_appr.status_code == 200

    draft = get_legal_document_draft(draft_id)
    assert draft["status"] == "APPROVED"
    assert draft.get("external_filing_reference") is None

    # 3. Packaging does NOT set status to FILED
    res_pkg = client.post(
        f"/api/documents/drafts/{draft_id}/package",
        json={"included_annexures": ["Custody Certificate"]},
        headers=headers_supervisor,
    )
    assert res_pkg.status_code == 200
    pkg = res_pkg.json()
    assert pkg["package_id"] is not None
    assert pkg["is_automatically_filed"] is False

    draft_after_pkg = get_legal_document_draft(draft_id)
    assert draft_after_pkg["status"] != "FILED"
    assert draft_after_pkg.get("external_filing_reference") is None


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 8: DLSA cannot mark source document VERIFIED unless authorized
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_08_dlsa_cannot_mark_source_document_verified():
    """DLSA Officer cannot perform statutory legal verification of source documents."""
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_officer")

    # Attempt to mark an uploaded document as legally VERIFIED
    res = client.post("/documents/doc_custody_utp0001/verify", headers=headers_dlsa)
    assert res.status_code == 403
    assert "access denied" in res.json()["detail"].lower() or "not authorized" in res.json()["detail"].lower() or "role" in res.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 9: DLSA cannot modify immutable approved document
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_09_dlsa_cannot_modify_immutable_approved_document():
    """Approved document is locked immutable; edits are blocked even if delegation is granted."""
    headers_supervisor = get_token_headers(Role.SUPERVISING_LEGAL_OFFICER.value, "demo_supervising")
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_officer")

    # Generate and approve draft
    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_supervisor,
    )
    draft_id = res_gen.json()["draft_id"]

    res_appr = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Approved and sealed by supervisor"},
        headers=headers_supervisor,
    )
    assert res_appr.status_code == 200

    # Grant delegation to DLSA
    now = datetime.now(timezone.utc)
    store_institutional_delegation({
        "delegation_id": "del_edit_test",
        "granted_to_user_id": "demo_dlsa_officer",
        "granted_to_role": "DLSA_OFFICER",
        "granted_by_user_id": "demo_supervising",
        "granted_by_role": "SUPERVISING_LEGAL_OFFICER",
        "organization_id": "org_dlsa_central",
        "jurisdiction": "Central Delhi",
        "capability": "CAN_EDIT_DOCUMENT_DRAFT",
        "allowed_document_types": ["tmpl_bnss_479_bail_v1"],
        "allowed_case_scope": ["UTP-0001"],
        "valid_from": (now - timedelta(minutes=5)).isoformat(),
        "valid_until": (now + timedelta(hours=2)).isoformat(),
        "status": "ACTIVE",
        "reason": "Delegated edit testing",
    })

    # Attempt to edit approved draft — MUST return 403 due to immutability
    res_edit = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Post-approval tampering attempt."},
        headers=headers_dlsa,
    )
    assert res_edit.status_code == 403
    assert "immutable" in res_edit.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 10: DLSA cannot access another advocate's unrelated case outside scope
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_10_dlsa_cannot_access_unrelated_case_outside_scope():
    """DLSA Officer cannot access draft endpoints for cases outside their authorized district."""
    headers_dlsa_west = get_token_headers(
        Role.DLSA_OFFICER.value,
        "demo_dlsa_west",
        org_id="org_dlsa_central",
        district="West Delhi",
    )

    # UTP-0001 is in Central Delhi
    res = client.get("/api/documents/drafts/case/UTP-0001", headers=headers_dlsa_west)
    assert res.status_code == 403
    assert "district" in res.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 11: DLSA can assign eligible counsel only when workflow permits
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_11_dlsa_can_assign_eligible_counsel_only_when_workflow_permits():
    """DLSA may only assign counsel when case stage is LEGAL_AID_REQUIRED and not already assigned."""
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_officer")

    # 1. UTP-0001 is already assigned to Adv. Rajesh Sharma
    res_already = client.post(
        "/cases/UTP-0001/assign-counsel",
        json={"lawyer_id": "demo_advocate_2", "lawyer_name": "Adv. Sunita Rao"},
        headers=headers_dlsa,
    )
    assert res_already.status_code == 400
    assert "already assigned" in res_already.json()["detail"].lower()

    # 2. Insert a fresh unassigned case in INTAKE stage
    _insert_test_case({
        "case_id": "UTP-UNASSIGNED-STAGE-TEST",
        "name": "Intake Stage Inmate",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
        "status": CaseState.INTAKE,
        "assignment_status": "AVAILABLE",
        "assigned_lawyer_id": None,
        "assigned_lawyer": None,
    })
    res_wrong_stage = client.post(
        "/cases/UTP-UNASSIGNED-STAGE-TEST/assign-counsel",
        json={"lawyer_id": "demo_advocate", "lawyer_name": "Adv. Rajesh Sharma"},
        headers=headers_dlsa,
    )
    assert res_wrong_stage.status_code == 400
    assert "must be 'legal_aid_required'" in res_wrong_stage.json()["detail"].lower()

    # 3. Transition to LEGAL_AID_REQUIRED and assign counsel
    update_case_status("UTP-UNASSIGNED-STAGE-TEST", CaseState.LEGAL_AID_REQUIRED)
    res_success = client.post(
        "/cases/UTP-UNASSIGNED-STAGE-TEST/assign-counsel",
        json={"lawyer_id": "demo_advocate", "lawyer_name": "Adv. Rajesh Sharma"},
        headers=headers_dlsa,
    )
    assert res_success.status_code == 200
    assert res_success.json()["status"] in ("success", "assigned")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 12: DLSA can request document preparation
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_12_dlsa_can_request_document_preparation():
    """DLSA Officer can create a document preparation requisition and UniversalTaskQueue task."""
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_officer")

    payload = {
        "case_id": "UTP-0001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "document_type": "BAIL_APPLICATION",
        "urgency": "URGENT",
        "reason": "Section 479 statutory threshold met (200 days detention).",
        "missing_prerequisites": ["custody_certificate"],
    }
    res = client.post(
        "/api/documents/drafts/request-preparation",
        json=payload,
        headers=headers_dlsa,
    )
    assert res.status_code in (200, 201)
    data = res.json()
    assert data["status"] == "DOCUMENT_PREPARATION_REQUESTED"
    assert "req_" in data["requisition_id"]
    assert data["task_id"] is not None

    # Check persistence in database
    db_req = get_document_preparation_requisition(data["requisition_id"])
    assert db_req is not None
    assert db_req["case_id"] == "UTP-0001"
    assert db_req["urgency"] == "URGENT"
    assert "custody_certificate" in db_req["missing_prerequisites"]


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 13: Valid delegation enables only the delegated capability
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_13_valid_delegation_enables_only_delegated_capability():
    """Valid delegation allows draft initiation but continues blocking approval, packaging, and filing."""
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_delegated")

    now = datetime.now(timezone.utc)
    store_institutional_delegation({
        "delegation_id": "del_initiate_only",
        "granted_to_user_id": "demo_dlsa_delegated",
        "granted_to_role": "DLSA_OFFICER",
        "granted_by_user_id": "demo_supervising",
        "granted_by_role": "SUPERVISING_LEGAL_OFFICER",
        "organization_id": "org_dlsa_central",
        "jurisdiction": "Central Delhi",
        "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
        "allowed_document_types": ["tmpl_bnss_479_bail_v1"],
        "allowed_case_scope": ["UTP-0001"],
        "valid_from": (now - timedelta(minutes=5)).isoformat(),
        "valid_until": (now + timedelta(hours=2)).isoformat(),
        "status": "ACTIVE",
        "reason": "Delegated draft initiation only",
    })

    # 1. Draft initiation succeeds
    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_dlsa,
    )
    assert res_gen.status_code == 201
    draft_id = res_gen.json()["draft_id"]

    # 2. Approval remains blocked (403)
    assert client.post(f"/api/documents/drafts/{draft_id}/approve", json={}, headers=headers_dlsa).status_code == 403

    # 3. Packaging remains blocked (403)
    assert client.post(f"/api/documents/drafts/{draft_id}/package", json={}, headers=headers_dlsa).status_code == 403

    # 4. Recording filing remains blocked (403)
    assert client.post(
        f"/api/documents/drafts/{draft_id}/record-filing",
        json={"filing_reference": "CNR-TEST"},
        headers=headers_dlsa,
    ).status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 14: Expired delegation disables capability
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_14_expired_delegation_disables_capability():
    """Delegation with valid_until in the past returns 403 Forbidden."""
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_expired")

    now = datetime.now(timezone.utc)
    store_institutional_delegation({
        "delegation_id": "del_expired_test",
        "granted_to_user_id": "demo_dlsa_expired",
        "granted_to_role": "DLSA_OFFICER",
        "granted_by_user_id": "demo_supervising",
        "granted_by_role": "SUPERVISING_LEGAL_OFFICER",
        "organization_id": "org_dlsa_central",
        "jurisdiction": "Central Delhi",
        "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
        "allowed_document_types": ["tmpl_bnss_479_bail_v1"],
        "allowed_case_scope": ["UTP-0001"],
        "valid_from": (now - timedelta(hours=5)).isoformat(),
        "valid_until": (now - timedelta(hours=1)).isoformat(),
        "status": "ACTIVE",
        "reason": "Expired test delegation",
    })

    res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_dlsa,
    )
    assert res.status_code == 403
    assert "delegation" in res.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 15: Revoked delegation disables capability immediately
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_15_revoked_delegation_disables_capability_immediately():
    """Revoking delegation immediately disables drafting power."""
    headers_supervisor = get_token_headers(Role.SUPERVISING_LEGAL_OFFICER.value, "demo_supervising")
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_revoked")

    now = datetime.now(timezone.utc)
    store_institutional_delegation({
        "delegation_id": "del_revocation_target",
        "granted_to_user_id": "demo_dlsa_revoked",
        "granted_to_role": "DLSA_OFFICER",
        "granted_by_user_id": "demo_supervising",
        "granted_by_role": "SUPERVISING_LEGAL_OFFICER",
        "organization_id": "org_dlsa_central",
        "jurisdiction": "Central Delhi",
        "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
        "allowed_document_types": ["tmpl_bnss_479_bail_v1"],
        "allowed_case_scope": ["UTP-0001"],
        "valid_from": (now - timedelta(minutes=5)).isoformat(),
        "valid_until": (now + timedelta(hours=2)).isoformat(),
        "status": "ACTIVE",
        "reason": "Pre-revocation delegation",
    })

    # 1. Draft generation works before revocation
    res_before = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_dlsa,
    )
    assert res_before.status_code == 201

    # 2. Supervisor revokes delegation
    res_revoke = client.post(
        "/api/documents/delegations/del_revocation_target/revoke",
        json={"reason": "Audit review concluded"},
        headers=headers_supervisor,
    )
    assert res_revoke.status_code == 200

    # 3. Subsequent draft generation MUST fail immediately with 403
    res_after = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_dlsa,
    )
    assert res_after.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 16: Delegation cannot cross organization scope
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_16_delegation_cannot_cross_organization_scope():
    """Delegation in org_dlsa_central does not grant access to cases in org_dlsa_east."""
    headers_dlsa = get_token_headers(
        Role.DLSA_OFFICER.value,
        "demo_dlsa_org_scoped",
        org_id="org_dlsa_central",
        district="Central Delhi",
    )

    now = datetime.now(timezone.utc)
    store_institutional_delegation({
        "delegation_id": "del_org_scope_test",
        "granted_to_user_id": "demo_dlsa_org_scoped",
        "granted_to_role": "DLSA_OFFICER",
        "granted_by_user_id": "demo_supervising",
        "granted_by_role": "SUPERVISING_LEGAL_OFFICER",
        "organization_id": "org_dlsa_central",
        "jurisdiction": "Central Delhi",
        "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
        "allowed_document_types": ["tmpl_bnss_479_bail_v1"],
        "allowed_case_scope": ["UTP-FOREIGN-02"],
        "valid_from": (now - timedelta(minutes=5)).isoformat(),
        "valid_until": (now + timedelta(hours=2)).isoformat(),
        "status": "ACTIVE",
        "reason": "Organization boundary test",
    })

    _insert_test_case({
        "case_id": "UTP-FOREIGN-02",
        "name": "East District Inmate",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_east",
        "status": CaseState.LEGAL_AID_REQUIRED,
    })

    res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-FOREIGN-02", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_dlsa,
    )
    assert res.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 17: Delegation cannot cross document-type scope
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_17_delegation_cannot_cross_document_type_scope():
    """Delegation restricted to bail template returns 403 on remand objection template."""
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_doc_scoped")

    now = datetime.now(timezone.utc)
    store_institutional_delegation({
        "delegation_id": "del_doc_scope_test",
        "granted_to_user_id": "demo_dlsa_doc_scoped",
        "granted_to_role": "DLSA_OFFICER",
        "granted_by_user_id": "demo_supervising",
        "granted_by_role": "SUPERVISING_LEGAL_OFFICER",
        "organization_id": "org_dlsa_central",
        "jurisdiction": "Central Delhi",
        "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
        "allowed_document_types": ["tmpl_bnss_479_bail_v1"],
        "allowed_case_scope": ["UTP-0001"],
        "valid_from": (now - timedelta(minutes=5)).isoformat(),
        "valid_until": (now + timedelta(hours=2)).isoformat(),
        "status": "ACTIVE",
        "reason": "Doc type scoping test",
    })

    # Attempting to generate remand objection with bail-only delegation
    res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_remand_objection_v1"},
        headers=headers_dlsa,
    )
    assert res.status_code == 403
    assert "delegation" in res.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 18: Frontend and backend capability state must match
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_18_frontend_and_backend_capability_state_match():
    """The /api/documents/delegations/my-active endpoint accurately reflects capability state."""
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, "demo_dlsa_query")

    # 1. Initially no delegation
    res_none = client.get(
        "/api/documents/delegations/my-active?case_id=UTP-0001&capability=CAN_INITIATE_DOCUMENT_DRAFT&document_type=tmpl_bnss_479_bail_v1",
        headers=headers_dlsa,
    )
    assert res_none.status_code == 200
    assert res_none.json()["is_delegated"] is False
    assert res_none.json()["delegation"] is None

    # 2. Grant delegation
    now = datetime.now(timezone.utc)
    store_institutional_delegation({
        "delegation_id": "del_query_test",
        "granted_to_user_id": "demo_dlsa_query",
        "granted_to_role": "DLSA_OFFICER",
        "granted_by_user_id": "demo_supervising",
        "granted_by_role": "SUPERVISING_LEGAL_OFFICER",
        "organization_id": "org_dlsa_central",
        "jurisdiction": "Central Delhi",
        "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
        "allowed_document_types": ["tmpl_bnss_479_bail_v1"],
        "allowed_case_scope": ["UTP-0001"],
        "valid_from": (now - timedelta(minutes=5)).isoformat(),
        "valid_until": (now + timedelta(hours=2)).isoformat(),
        "status": "ACTIVE",
        "reason": "Capability match test",
    })

    # 3. Query returns active delegation matching backend guard
    res_active = client.get(
        "/api/documents/delegations/my-active?case_id=UTP-0001&capability=CAN_INITIATE_DOCUMENT_DRAFT&document_type=tmpl_bnss_479_bail_v1",
        headers=headers_dlsa,
    )
    assert res_active.status_code == 200
    assert res_active.json()["is_delegated"] is True
    assert res_active.json()["delegation"]["delegation_id"] == "del_query_test"

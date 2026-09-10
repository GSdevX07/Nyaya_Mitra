"""
test_stage19_supervisor_role_hardening.py - Comprehensive Test Suite for Supervising Legal Officer Role Hardening.
=================================================================================================================
Validates the institutional supervisory legal review layer according to Stage 19 specifications:
1.  Cross-district dossier access denial (403 Forbidden).
2.  Cross-organization case access denial (403 Forbidden).
3.  Scoped GET /cases returns only matters in supervisor's organization and district.
4.  Supervisor can inspect exact case facts.
5.  Supervisor can inspect source documents and evidence records.
6.  Supervisor can inspect retrieved legal citations and statutory authorities.
7.  Supervisor can inspect pre-approval readiness evaluation results.
8.  Blocked readiness rejects supervisory approval (400 Bad Request).
9.  Cleared readiness allows supervisory Level-2 approval (status=APPROVED, is_immutable=True).
10. Approved draft is permanently locked and immutable (subsequent edits blocked with 403).
11. Original machine-generated AI draft is protected from deletion or silent modification.
12. Supervisory approval requires valid workflow state (SUBMITTED with prior counsel sign-off).
13. AI actor / automated service cannot issue supervisory approval (Human-only gating).
14. Supervisor can record supervisory review comments and directives.
15. Request revisions preserves current version and records directives.
16. Request revisions automatically routes operational task to assigned defense counsel in UniversalTaskQueue.
17. Request revisions transitions workflow state back to HUMAN_REVIEW.
18. Supervisor can inspect side-by-side version diff comparisons.
19. Automatic court filing by supervisor is strictly blocked (reserved for assigned defense counsel).
20. Judicial decisions are external; supervisor cannot forge or pronounce judicial orders.
"""

import pytest
import uuid
import datetime
import json
from fastapi.testclient import TestClient

from app.main import app
from app.auth.roles import Role
from app.auth.tokens import create_access_token
from app.database import (
    init_db,
    get_case,
    get_db_connection,
    _MEMORY_CASES,
    store_legal_document_draft,
    get_legal_document_draft,
    store_matter_artifact_version,
    store_matter_approval,
)
from app.models.schemas import CaseRecord, CaseState
from app.services.document_templates import seed_default_templates
from app.repositories.task_repository import get_task_repository

client = TestClient(app)


def _insert_test_case(case_dict: dict) -> CaseRecord:
    cid = case_dict.get("case_id", "CASE-TEST-001")
    defaults = {
        "case_id": cid,
        "name": f"Undertrial {cid}",
        "prisoner_category": "UNDERTRIAL",
        "legal_code": "BNS_2023",
        "offense_sections": ["Section 303", "Section 479"],
        "arrest_date": "2024-03-01",
        "custody_days": 180,
        "max_sentence_days_for_offense": 730,
        "punishable_by_death_or_life": False,
        "multiple_active_cases": False,
        "required_docs": ["remand_order", "charge_sheet", "custody_certificate"],
        "present_docs": ["remand_order", "charge_sheet", "custody_certificate"],
        "urgency_flags": {"age": 32, "health_flag": False, "repeat_offender": False},
        "jail_location": "Tihar Central Jail No. 4",
        "district": "Central Delhi",
        "state": "Delhi",
        "court_name": "Central District Court, Tis Hazari",
        "police_station": "Kotwali",
        "fir_number": "FIR-2024-0101",
        "parent_name": "Harbans Singh",
        "assignment_status": "ASSIGNED",
        "assigned_lawyer_id": "demo_advocate",
        "assigned_lawyer": "Adv. Rajesh Sharma",
        "data_source_status": "DEMO_SYNTHETIC",
        "status": "SUBMITTED",
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
    return case_rec


@pytest.fixture(autouse=True)
def setup_clean_db():
    init_db()
    seed_default_templates()


def _make_token(
    user_id: str = "demo_supervising",
    role: str = Role.SUPERVISING_LEGAL_OFFICER.value,
    org_id: str = "org_dlsa_central",
    district: str = "Central Delhi",
    authorized_district_ids: list | None = None,
) -> str:
    extra = {
        "district": district,
        "authorized_district_ids": authorized_district_ids or [district],
    }
    return create_access_token(
        subject=user_id,
        role=role,
        org_id=org_id,
        extra_claims=extra,
    )


def _auth_headers(
    user_id: str = "demo_supervising",
    role: str = Role.SUPERVISING_LEGAL_OFFICER.value,
    org_id: str = "org_dlsa_central",
    district: str = "Central Delhi",
    authorized_district_ids: list | None = None,
) -> dict:
    tok = _make_token(user_id, role, org_id, district, authorized_district_ids)
    return {"Authorization": f"Bearer {tok}"}


# ── 1. Cross-District Dossier Access Denial ───────────────────────────────────

def test_scenario_01_cross_district_dossier_access_blocked():
    """Supervisor in Central Delhi accessing case in South Delhi receives 403 Forbidden."""
    _insert_test_case({
        "case_id": "CASE-SOUTH-001",
        "district": "South Delhi",
        "organization_id": "org_dlsa_central",
    })
    headers_central = _auth_headers(district="Central Delhi", authorized_district_ids=["Central Delhi"])
    res = client.get("/cases/CASE-SOUTH-001", headers=headers_central)
    assert res.status_code == 403


# ── 2. Cross-Organization Case Access Denial ──────────────────────────────────

def test_scenario_02_cross_organization_dossier_access_blocked():
    """Supervisor in org_dlsa_central accessing case in org_dlsa_south receives 403 Forbidden."""
    _insert_test_case({
        "case_id": "CASE-SOUTH-ORG-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_south",
    })
    headers_central = _auth_headers(org_id="org_dlsa_central")
    res = client.get("/cases/CASE-SOUTH-ORG-001", headers=headers_central)
    assert res.status_code == 403


# ── 3. Scoped GET /cases returns only in-scope matters ────────────────────────

def test_scenario_03_scoped_get_cases_returns_only_organization_and_district_matters():
    """GET /cases returns only matters in supervisor's authorized organization and district."""
    _insert_test_case({"case_id": "CASE-SCOPED-CENTRAL", "district": "Central Delhi", "organization_id": "org_dlsa_central"})
    _insert_test_case({"case_id": "CASE-SCOPED-SOUTH", "district": "South Delhi", "organization_id": "org_dlsa_central"})
    _insert_test_case({"case_id": "CASE-SCOPED-OTHER-ORG", "district": "Central Delhi", "organization_id": "org_dlsa_mumbai"})

    headers = _auth_headers(district="Central Delhi", org_id="org_dlsa_central", authorized_district_ids=["Central Delhi"])
    res = client.get("/cases", headers=headers)
    assert res.status_code == 200
    cases = res.json()
    case_ids = [c["case"]["case_id"] for c in cases]
    assert "CASE-SCOPED-CENTRAL" in case_ids
    assert "CASE-SCOPED-SOUTH" not in case_ids
    assert "CASE-SCOPED-OTHER-ORG" not in case_ids


# ── 4. Supervisor Inspects Exact Case Facts ───────────────────────────────────

def test_scenario_04_supervisor_can_inspect_case_facts():
    """Supervisor can inspect exact case facts and detention timeline on authorized matters."""
    _insert_test_case({
        "case_id": "CASE-FACTS-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
        "custody_days": 180,
    })
    headers = _auth_headers()
    res = client.get("/cases/CASE-FACTS-001", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["case"]["custody_days"] == 180
    assert data["case"]["police_station"] == "Kotwali"


# ── 5. Supervisor Inspects Source Documents & Evidence ────────────────────────

def test_scenario_05_supervisor_can_inspect_source_documents():
    """Supervisor can inspect present vs required documents and verify evidence integrity."""
    _insert_test_case({
        "case_id": "CASE-EVID-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
    })
    headers = _auth_headers()
    res = client.get("/cases/CASE-EVID-001", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "remand_order" in data["case"]["present_docs"]


# ── 6. Supervisor Inspects Legal Citations & Statutory Grounding ──────────────

def test_scenario_06_supervisor_can_inspect_retrieved_legal_citations():
    """Supervisor can view statutory grounding and legal knowledge base."""
    headers = _auth_headers()
    res = client.get("/api/documents/templates", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["templates"]) >= 3
    statutory_grounds = [t.get("statutory_ground") for t in data["templates"]]
    assert any("479" in g for g in statutory_grounds if g)


# ── 7. Supervisor Inspects Pre-Approval Readiness Results ─────────────────────

def test_scenario_07_supervisor_can_inspect_pre_approval_readiness_evaluation():
    """Supervisor can fetch pre-approval readiness check breakdown for a draft."""
    _insert_test_case({
        "case_id": "CASE-READINESS-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
    })
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "CASE-READINESS-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "DRAFT",
        "is_immutable": False,
        "content_text": "Grounds for bail: The applicant has completed one-third detention. [MISSING: POLICE_STATION]",
        "exact_case_facts": {
            "name": "Undertrial CASE-READINESS-001",
            "court_name": "Central District Court, Tis Hazari",
            "custody_days": 120,
            "offense_sections": ["Section 303 BNS", "Section 479 BNSS"],
        },
        "source_citations": ["Section 479 BNSS"],
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    res = client.get(f"/api/documents/drafts/{draft_id}/readiness", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["can_approve"] is False
    assert data["total_blocking_issues"] > 0
    assert any("POLICE_STATION" in str(issue) for issue in data["blocking_issues"])


# ── 8. Blocked Readiness Rejects Supervisory Approval ─────────────────────────

def test_scenario_08_blocked_readiness_prevents_supervisory_approval():
    """Supervisory approval is strictly rejected (400 Bad Request) when draft has blocking readiness issues."""
    _insert_test_case({
        "case_id": "CASE-BLOCKED-APP-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
    })
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "CASE-BLOCKED-APP-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "DRAFT",
        "is_immutable": False,
        "content_text": "Applicant detained under [MISSING: OFFENSE_SECTION].",
        "exact_case_facts": {
            "name": "Undertrial CASE-BLOCKED-APP-001",
            "court_name": "Central District Court, Tis Hazari",
            "custody_days": 120,
            "offense_sections": ["Section 303 BNS"],
        },
        "source_citations": [],
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    res = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Supervisory approval attempt on defective draft."},
        headers=headers,
    )
    assert res.status_code == 400
    err = res.json()
    assert "Pre-approval readiness check failed" in str(err)


# ── 9. Cleared Readiness Allows Supervisory Approval ──────────────────────────

def test_scenario_09_cleared_readiness_allows_supervisory_level2_approval():
    """Cleared readiness allows supervisor to grant Level-2 institutional sign-off."""
    _insert_test_case({
        "case_id": "CASE-CLEARED-APP-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
        "status": "SUBMITTED",
    })
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "CASE-CLEARED-APP-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "DRAFT",
        "is_immutable": False,
        "content_text": (
            "IN THE COURT OF Central District Court, Tis Hazari\n"
            "APPLICATION FOR BAIL UNDER SECTION 479 BNSS\n"
            "IN THE MATTER OF Undertrial CASE-CLEARED-APP-001\n"
            "MOST RESPECTFULLY SHOWETH:\n"
            "1. The applicant has served 120 days custody for Section 303 BNS.\n"
            "2. Satisfies statutory threshold under Section 479 BNSS.\n"
            "PRAYER:\n"
            "It is prayed that applicant be admitted to bail."
        ),
        "exact_case_facts": {
            "name": "Undertrial CASE-CLEARED-APP-001",
            "accused_name": "Undertrial CASE-CLEARED-APP-001",
            "court_name": "Central District Court, Tis Hazari",
            "district": "Central Delhi",
            "fir_number": "FIR-2024-0101",
            "police_station": "Kotwali Police Station",
            "offense_sections": ["Section 303 BNS", "Section 479 BNSS"],
            "custody_days": 120,
            "max_sentence_days_for_offense": 730,
            "statutory_threshold_fraction": "one-third (1/3)",
            "threshold_days": 120,
            "assigned_lawyer": "Adv. Rajesh Sharma",
            "present_docs": ["remand_order", "charge_sheet", "custody_certificate"],
        },
        "source_documents": ["remand_order", "charge_sheet", "custody_certificate"],
        "source_citations": ["Section 479 BNSS", "Section 303 BNS"],
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    res = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Supervisory review completed. Section 479 BNSS grounds verified."},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "APPROVED"
    assert data["is_immutable"] is True


# ── 10. Approved Draft is Permanently Immutable ───────────────────────────────

def test_scenario_10_approved_draft_is_permanently_immutable():
    """Approved draft cannot be modified directly (403 Forbidden)."""
    _insert_test_case({
        "case_id": "CASE-IMMUTABLE-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
    })
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "CASE-IMMUTABLE-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "APPROVED",
        "is_immutable": True,
        "content_text": "Immutable approved bail petition.",
        "exact_case_facts": {"court_name": "Tis Hazari"},
        "created_by": "demo_supervising",
        "created_by_role": "SUPERVISING_LEGAL_OFFICER",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    res = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Unauthorized modification attempt to immutable approved version."},
        headers=headers,
    )
    assert res.status_code == 403


# ── 11. Original AI Draft is Protected ────────────────────────────────────────

def test_scenario_11_original_ai_draft_is_protected():
    """Supervisor cannot directly modify counsel work product or delete machine original."""
    _insert_test_case({
        "case_id": "CASE-AI-PROT-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
    })
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "CASE-AI-PROT-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "DRAFT",
        "is_immutable": False,
        "original_ai_text": "Original machine-generated baseline petition.",
        "content_text": "Working counsel draft text.",
        "exact_case_facts": {"court_name": "Tis Hazari"},
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    # Direct edit attempt by supervisor is blocked (must use request-revisions)
    res = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Supervisor trying to edit counsel draft directly."},
        headers=headers,
    )
    assert res.status_code == 403


# ── 12. Supervisory Approval Requires Valid Workflow State ────────────────────

def test_scenario_12_supervisory_approval_requires_valid_workflow_state():
    """Supervisor attempting to approve matter not in SUBMITTED state is rejected."""
    _insert_test_case({
        "case_id": "CASE-INVALID-STATE-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
        "status": "INTAKE",
    })
    headers = _auth_headers()
    res = client.post(
        "/api/cases/CASE-INVALID-STATE-001/transitions",
        json={"transition": "SUPERVISORY_APPROVE", "payload": {}},
        headers=headers,
    )
    assert res.status_code in (400, 403)


# ── 13. Non-Human / AI Actor Cannot Issue Supervisory Approval ────────────────

def test_scenario_13_ai_actor_cannot_issue_supervisory_approval():
    """AI agent / automated service attempting SUPERVISORY_APPROVE is blocked."""
    _insert_test_case({
        "case_id": "CASE-AI-APP-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
        "status": "SUBMITTED",
    })
    token_ai = create_access_token(
        subject="ai_service",
        role=Role.INTEGRATION_SERVICE.value,
        org_id="org_dlsa_central",
    )
    res = client.post(
        "/api/cases/CASE-AI-APP-001/transitions",
        json={"transition": "SUPERVISORY_APPROVE", "payload": {}},
        headers={"Authorization": f"Bearer {token_ai}"},
    )
    assert res.status_code == 403


# ── 14. Supervisor Records Review Comments ────────────────────────────────────

def test_scenario_14_supervisor_can_add_supervisory_comments():
    """Supervisor can record review comments and directives on drafts."""
    _insert_test_case({
        "case_id": "CASE-COMMENT-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
    })
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "CASE-COMMENT-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "DRAFT",
        "is_immutable": False,
        "content_text": "Working petition draft.",
        "exact_case_facts": {"court_name": "Tis Hazari"},
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    res = client.post(
        f"/api/documents/drafts/{draft_id}/comments",
        json={"comment": "Supervisory review: Please verify parity ground under Section 479(1) proviso."},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert any("parity ground" in c.get("comment", "") for c in data.get("reviewer_comments", []))


# ── 15. Request Revisions Preserves Current Version ───────────────────────────

def test_scenario_15_request_revisions_preserves_current_version():
    """Request revisions records directives and preserves current version without destroying content."""
    _insert_test_case({
        "case_id": "CASE-REV-PRESERV-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
        "status": "SUBMITTED",
    })
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "CASE-REV-PRESERV-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "DRAFT",
        "is_immutable": False,
        "content_text": "Original draft petition text by counsel.",
        "exact_case_facts": {"court_name": "Tis Hazari"},
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    res = client.post(
        f"/api/documents/drafts/{draft_id}/request-revisions",
        json={"reason": "Specify medical history and delay exclusions in paragraph 4."},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REVISIONS_REQUESTED"
    assert data["content_text"] == "Original draft petition text by counsel."


# ── 16. Request Revisions Enqueues Task for Assigned Counsel ──────────────────

def test_scenario_16_request_revisions_enqueues_task_for_assigned_counsel():
    """Requesting revisions automatically enqueues a high-priority task for assigned counsel in UniversalTaskQueue."""
    _insert_test_case({
        "case_id": "CASE-TASK-ROUTING-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
        "assigned_lawyer_id": "adv_rajesh_sharma",
        "status": "SUBMITTED",
    })
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "CASE-TASK-ROUTING-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "DRAFT",
        "is_immutable": False,
        "content_text": "Draft awaiting revisions.",
        "exact_case_facts": {"court_name": "Tis Hazari"},
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    res = client.post(
        f"/api/documents/drafts/{draft_id}/request-revisions",
        json={"reason": "Add Supreme Court precedent Satender Kumar Antil (2022)."},
        headers=headers,
    )
    assert res.status_code == 200

    # Verify task queue has new task for defense advocate
    repo = get_task_repository()
    tasks = repo.get_tasks_for_case("CASE-TASK-ROUTING-001")
    rev_tasks = [t for t in tasks if (t.get("task_type") if isinstance(t, dict) else getattr(t, "task_type", None)) == "REVISE_PETITION"]
    assert len(rev_tasks) >= 1
    t0 = rev_tasks[0]
    role = t0.get("owner_role") if isinstance(t0, dict) else getattr(t0, "owner_role", None)
    priority = t0.get("priority") if isinstance(t0, dict) else getattr(t0, "priority", None)
    assert role == "DEFENSE_ADVOCATE"
    assert priority == "HIGH"


# ── 17. Request Revisions Transitions State to HUMAN_REVIEW ───────────────────

def test_scenario_17_request_revisions_transitions_state_to_human_review():
    """Requesting revisions transitions case workflow state back to HUMAN_REVIEW."""
    _insert_test_case({
        "case_id": "CASE-TRANS-REV-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
        "status": "SUBMITTED",
    })
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "CASE-TRANS-REV-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "DRAFT",
        "is_immutable": False,
        "content_text": "Draft content.",
        "exact_case_facts": {"court_name": "Tis Hazari"},
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    res = client.post(
        f"/api/documents/drafts/{draft_id}/request-revisions",
        json={"reason": "Clarify Section 479 computation."},
        headers=headers,
    )
    assert res.status_code == 200

    c = get_case("CASE-TRANS-REV-001")
    assert str(c.status) in ("HUMAN_REVIEW", "CaseState.HUMAN_REVIEW", "LAWYER_REVIEW")


# ── 18. Supervisor Can Diff Draft Versions ────────────────────────────────────

def test_scenario_18_supervisor_can_diff_draft_versions():
    """Supervisor can compare versions side-by-side with line-level diffing."""
    _insert_test_case({
        "case_id": "CASE-DIFF-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
    })
    d1_id = f"draft_{uuid.uuid4().hex[:8]}"
    d2_id = f"draft_{uuid.uuid4().hex[:8]}"

    store_legal_document_draft({
        "draft_id": d1_id,
        "case_id": "CASE-DIFF-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "APPROVED",
        "is_immutable": True,
        "content_text": "Line 1: Bail Petition\nLine 2: Section 436A CrPC grounds.",
        "exact_case_facts": {"court_name": "Tis Hazari"},
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    store_legal_document_draft({
        "draft_id": d2_id,
        "case_id": "CASE-DIFF-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 2,
        "parent_version_id": d1_id,
        "status": "DRAFT",
        "is_immutable": False,
        "content_text": "Line 1: Bail Petition\nLine 2: Section 479 BNSS statutory grounds updated.",
        "exact_case_facts": {"court_name": "Tis Hazari"},
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    res = client.get(f"/api/documents/drafts/diff?draft_a_id={d1_id}&draft_b_id={d2_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "diff_lines" in data
    assert data["lines_added"] > 0
    assert data["lines_deleted"] > 0


# ── 19. Automatic Court Filing by Supervisor is Blocked ───────────────────────

def test_scenario_19_automatic_court_filing_by_supervisor_is_blocked():
    """Supervisor attempting to record court filing directly receives 403 Forbidden."""
    _insert_test_case({
        "case_id": "CASE-FILING-BLOCK-001",
        "district": "Central Delhi",
        "organization_id": "org_dlsa_central",
        "status": "APPROVED",
    })
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": "CASE-FILING-BLOCK-001",
        "template_id": "tmpl_bnss_479_bail_v1",
        "organization_id": "org_dlsa_central",
        "version_number": 1,
        "status": "APPROVED",
        "is_immutable": True,
        "content_text": "Approved draft ready for filing by counsel.",
        "exact_case_facts": {"court_name": "Tis Hazari"},
        "created_by": "Adv. Rajesh Sharma",
        "created_by_role": "DEFENSE_ADVOCATE",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

    headers = _auth_headers()
    res = client.post(
        f"/api/documents/drafts/{draft_id}/record-filing",
        json={"filing_reference": "CNR-DL-2026-0001"},
        headers=headers,
    )
    assert res.status_code == 403


# ── 20. Judicial Decisions are External & Protected ───────────────────────────

def test_scenario_20_judicial_decisions_are_external():
    """Supervisor cannot forge or pronounce judicial orders; system only records actual court orders."""
    headers = _auth_headers()
    # Attempting unauthorized actions trigger
    res = client.post("/actions/trigger?action_id=ACT-UTP-0001-COURT_FILE", headers=headers)
    assert res.status_code == 403

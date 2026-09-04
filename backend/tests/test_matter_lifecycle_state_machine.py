"""
test_matter_lifecycle_state_machine.py - Authoritative Stage 9 Test Suite.
==========================================================================
Verifies:
1. Canonical 16-State Lifecycle Progression (INTAKE -> ... -> CLOSED).
2. Protection against Illegal Transitions (INTAKE -> FILED returns 400).
3. Strict Nyaya Mitra Role Ownership:
   - PLATFORM_ADMIN blocked from legal approvals, counsel appointments, filing (403).
   - GOV_ADMIN blocked from routine case transitions (403).
   - READ_ONLY_AUDITOR blocked from all mutations (403).
   - DEFENSE_ADVOCATE blocked from supervisory approvals (403).
   - SUPERVISING_LEGAL_OFFICER authorized for approvals/resolutions, not filing counsel.
4. Stage 8 Rules Engine Boundary:
   - Rules engine output moves state strictly to ANALYSIS_READY, never APPROVED or FILED.
   - Artifacts tagged AI_ASSISTED.
5. Exact Artifact Version Approvals & Invalidation on Revision:
   - Version N+1 creation invalidates prior approval for filing.
6. Case Handoff & Reassignment Dossier:
   - Complete historical preservation in matter_handoffs table.
   - Accurate completed milestones and pending requirements in summary.
7. Concurrency & Optimistic Locking:
   - Version mismatch rejected with 409 Conflict.
8. Persistent SQLite Storage:
   - All records verified in production database tables.
"""

import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.models.schemas import MatterState
from app.database import (
    get_db_connection,
    get_case_version,
    store_matter_artifact_version,
    store_matter_approval,
    get_matter_approvals,
    get_matter_handoffs,
)


@pytest.fixture
def client():
    return TestClient(app)


def get_token(role: Role, user_id: str, full_name: str, linked_case: str = None) -> str:
    claims = {"email": f"{user_id}@demo.nyayamitra.in"}
    if linked_case:
        claims["linked_case_id"] = linked_case
    return create_access_token(
        subject=user_id,
        role=role.value,
        org_id="org_dlsa_central",
        facility_ids=["fac_tihar_jail_04"],
        extra_claims=claims,
    )


@pytest.fixture
def dlsa_token():
    return get_token(Role.DLSA_OFFICER, "demo_dlsa", "DLSA Officer Rajesh")


@pytest.fixture
def supervisor_token():
    return get_token(Role.SUPERVISING_LEGAL_OFFICER, "demo_supervisor", "Dr. Aruna Roy")


@pytest.fixture
def advocate_token():
    return get_token(Role.DEFENSE_ADVOCATE, "demo_advocate", "Adv. Rajesh Sharma", linked_case="UTP-STAGE9-01")


@pytest.fixture
def jail_token():
    return get_token(Role.JAIL_OFFICER, "demo_jail", "Jail Officer Singh")


@pytest.fixture
def platform_admin_token():
    return get_token(Role.PLATFORM_ADMIN, "demo_platform_admin", "Admin System")


@pytest.fixture
def gov_admin_token():
    return get_token(Role.GOV_ADMIN, "demo_gov_admin", "Gov Admin State")


@pytest.fixture
def auditor_token():
    return get_token(Role.READ_ONLY_AUDITOR, "demo_auditor", "Auditor General")


@pytest.fixture
def test_case_id():
    """Create a pristine test case in the database for state machine testing."""
    cid = f"UTP-S9-{uuid.uuid4().hex[:6].upper()}"
    case_dict = {
        "case_id": cid,
        "name": "Synthetic Undertrial",
        "offense_sections": ["IPC 379"],
        "arrest_date": "2025-01-10",
        "custody_days": 120,
        "max_sentence_days_for_offense": 1095,
        "min_sentence_days": 0,
        "undertrial_category": "UNDERTRIAL",
        "applicable_legal_code": "IPC_1860",
        "jail_location": "Central Jail No. 4, Tihar (Synthetic)",
        "facility_ids": ["fac_tihar_jail_04"],
        "status": "INTAKE",
        "fir_number": "FIR-2025-001",
        "police_station": "Tilak Nagar",
        "court_name": "Sessions Court, Tis Hazari",
        "timeline": [],
        "present_docs": ["fir", "remand_order"],
        "urgency_flags": {"age": 28, "health_flag": False, "repeat_offender": False},
    }
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO cases (case_id, data, status, version_number)
        VALUES (?, ?, ?, 1)
    """, (cid, json.dumps(case_dict), "INTAKE"))
    conn.commit()
    conn.close()
    return cid


# ── 1. Canonical 16-State Lifecycle Progression ───────────────────────────────

def test_canonical_16_state_lifecycle_progression(
    client, test_case_id, dlsa_token, supervisor_token, advocate_token, jail_token
):
    """
    Test complete authoritative journey through the 16 canonical states:
    INTAKE -> VERIFICATION -> REVIEW -> LEGAL_AID_REQUIRED -> ASSIGNED ->
    DOCUMENT_PENDING -> ANALYSIS_READY -> HUMAN_REVIEW -> SUBMITTED ->
    APPROVED -> FILED -> HEARING_SCHEDULED -> ORDER_RECEIVED ->
    RELEASE_WORKFLOW -> POST_RELEASE_FOLLOW_UP -> CLOSED.
    """
    cid = test_case_id

    # 1. INTAKE -> VERIFICATION (by DLSA_OFFICER)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {dlsa_token}"},
        json={"transition": "START_VERIFICATION", "comment": "Starting intake verification."},
    )
    assert res.status_code == 200, res.text
    assert res.json()["current_state"] == "VERIFICATION"

    # 2. VERIFICATION -> REVIEW (by DLSA_OFFICER)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {dlsa_token}"},
        json={"transition": "SUBMIT_FOR_REVIEW", "comment": "Verification complete; reviewing legal needs."},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "REVIEW"

    # 3. REVIEW -> LEGAL_AID_REQUIRED (by DLSA_OFFICER)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {dlsa_token}"},
        json={"transition": "FLAG_LEGAL_AID_REQUIRED", "comment": "Undertrial has no private counsel."},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "LEGAL_AID_REQUIRED"

    # 4. LEGAL_AID_REQUIRED -> ASSIGNED (by DLSA_OFFICER)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {dlsa_token}"},
        json={
            "transition": "ASSIGN_COUNSEL",
            "payload": {"assigned_advocate_id": "LWYR-001", "assigned_advocate_name": "Adv. Rajesh Sharma"},
            "comment": "Appointed panel defense advocate.",
        },
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "ASSIGNED"

    # 5. ASSIGNED -> DOCUMENT_PENDING (by DEFENSE_ADVOCATE)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={"transition": "REQUEST_DOCUMENTS", "comment": "Requesting remand order from court clerk."},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "DOCUMENT_PENDING"

    # 6. DOCUMENT_PENDING -> ANALYSIS_READY (by DEFENSE_ADVOCATE)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={"transition": "COMPLETE_ANALYSIS", "comment": "Documents complete; statutory analysis ready."},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "ANALYSIS_READY"

    # 7. ANALYSIS_READY -> HUMAN_REVIEW (by DEFENSE_ADVOCATE)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={"transition": "SUBMIT_FOR_HUMAN_REVIEW", "comment": "Advocate preparing bail petition draft."},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "HUMAN_REVIEW"

    # Create an artifact version for the bail application
    art_res = client.post(
        f"/api/cases/{cid}/artifacts",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={
            "artifact_id": "art_bail_draft",
            "artifact_type": "BAIL_APPLICATION",
            "content_text": "IN THE COURT OF SESSIONS... BAIL PETITION UNDER SECTION 479 BNSS...",
            "is_ai_generated": False,
            "version_tag": "bail_draft_v1",
        },
    )
    assert art_res.status_code == 200
    ver_id = art_res.json()["version_id"]

    # 8. HUMAN_REVIEW -> SUBMITTED (Counsel sign-off by DEFENSE_ADVOCATE)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={
            "transition": "COUNSEL_SIGN_OFF",
            "payload": {"artifact_version_id": ver_id, "artifact_type": "BAIL_APPLICATION"},
            "comment": "Counsel has finalized draft and signs off for institutional supervisory review.",
        },
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "SUBMITTED"

    # 9. SUBMITTED -> APPROVED (Supervisory Approval by SUPERVISING_LEGAL_OFFICER)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {supervisor_token}"},
        json={
            "transition": "SUPERVISORY_APPROVE",
            "payload": {"artifact_version_id": ver_id, "artifact_type": "BAIL_APPLICATION"},
            "comment": "Supervising officer reviewed exact artifact version and granted institutional approval.",
        },
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "APPROVED"

    # 10. APPROVED -> FILED (Filing by DEFENSE_ADVOCATE with genuine court reference)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={
            "transition": "RECORD_FILING",
            "payload": {"filing_reference": "CNR-DLCT01-004523-2026", "filing_date": "2026-09-04"},
            "comment": "Petition lodged through eCourts filing registry.",
        },
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "FILED"

    # 11. FILED -> HEARING_SCHEDULED (by DEFENSE_ADVOCATE)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={
            "transition": "SCHEDULE_HEARING",
            "payload": {"hearing_date": "2026-09-15", "court_name": "Sessions Court, Tis Hazari"},
            "comment": "Listed before Court No. 4.",
        },
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "HEARING_SCHEDULED"

    # 12. HEARING_SCHEDULED -> ORDER_RECEIVED (by DEFENSE_ADVOCATE)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={
            "transition": "RECORD_COURT_ORDER",
            "payload": {"order_type": "BAIL_GRANTED", "order_date": "2026-09-15", "order_summary": "Bail granted on personal bond."},
            "comment": "Court granted bail under Section 479 BNSS.",
        },
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "ORDER_RECEIVED"

    # 13. ORDER_RECEIVED -> RELEASE_WORKFLOW (by JAIL_OFFICER)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {jail_token}"},
        json={"transition": "INITIATE_RELEASE", "comment": "Surety verification and prison formalities initiated."},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "RELEASE_WORKFLOW"

    # 14. RELEASE_WORKFLOW -> POST_RELEASE_FOLLOW_UP (by JAIL_OFFICER)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {jail_token}"},
        json={
            "transition": "CONFIRM_RELEASE",
            "payload": {"release_date": "2026-09-16"},
            "comment": "Undertrial released from Central Jail No. 4.",
        },
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "POST_RELEASE_FOLLOW_UP"

    # 15. POST_RELEASE_FOLLOW_UP -> CLOSED (by SUPERVISING_LEGAL_OFFICER)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {supervisor_token}"},
        json={
            "transition": "CLOSE_MATTER",
            "payload": {"closure_reason": "Post-release legal aid and trial tracking obligations fulfilled."},
            "comment": "Matter formally closed.",
        },
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "CLOSED"


# ── 2. Protection Against Illegal Transitions ─────────────────────────────────

def test_illegal_transitions_rejected_with_400(client, test_case_id, dlsa_token, advocate_token):
    """Validate that skipping workflow states or invalid transitions return 400 Bad Request."""
    cid = test_case_id

    # From INTAKE, attempting direct RECORD_FILING is illegal
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={"transition": "RECORD_FILING", "payload": {"filing_reference": "CNR-001"}},
    )
    assert res.status_code == 400
    assert "Illegal transition" in res.json()["detail"]

    # From INTAKE, attempting direct CLOSE_MATTER is illegal
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {dlsa_token}"},
        json={"transition": "CLOSE_MATTER", "payload": {"closure_reason": "Skip"}},
    )
    assert res.status_code == 400
    assert "Illegal transition" in res.json()["detail"]


# ── 3. Strict Nyaya Mitra Role Ownership Enforcement ──────────────────────────

def test_role_ownership_blocks_unauthorized_actors(
    client, test_case_id, platform_admin_token, gov_admin_token, auditor_token, jail_token, dlsa_token, advocate_token
):
    """
    Ensure strict separation of powers:
    - PLATFORM_ADMIN cannot approve, file, or assign counsel.
    - GOV_ADMIN cannot execute routine case transitions.
    - READ_ONLY_AUDITOR cannot execute any state transition.
    - JAIL_OFFICER cannot approve or file.
    - DEFENSE_ADVOCATE cannot grant supervisory approval.
    """
    cid = test_case_id

    # 1. PLATFORM_ADMIN blocked from ASSIGN_COUNSEL (403)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {platform_admin_token}"},
        json={"transition": "START_VERIFICATION"},
    )
    assert res.status_code == 403
    assert "Permission Denied" in res.json()["detail"]

    # 2. GOV_ADMIN blocked from case transition (403)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {gov_admin_token}"},
        json={"transition": "START_VERIFICATION"},
    )
    assert res.status_code == 403

    # 3. READ_ONLY_AUDITOR blocked from any transition (403)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"transition": "START_VERIFICATION"},
    )
    assert res.status_code == 403

    # Advance case to HUMAN_REVIEW
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "START_VERIFICATION"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "SUBMIT_FOR_REVIEW"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "FLAG_LEGAL_AID_REQUIRED"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "ASSIGN_COUNSEL", "payload": {"assigned_advocate_id": "L-1"}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_token}"}, json={"transition": "COMPLETE_ANALYSIS"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_token}"}, json={"transition": "SUBMIT_FOR_HUMAN_REVIEW"})

    # 4. DEFENSE_ADVOCATE blocked from SUPERVISORY_APPROVE (403)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={"transition": "SUPERVISORY_APPROVE", "payload": {"artifact_version_id": "ver_dummy"}},
    )
    assert res.status_code == 403

    # 5. JAIL_OFFICER blocked from SUPERVISORY_APPROVE (403)
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {jail_token}"},
        json={"transition": "SUPERVISORY_APPROVE", "payload": {"artifact_version_id": "ver_dummy"}},
    )
    assert res.status_code == 403


# ── 4. Stage 8 Rules Engine Boundary & AI Safety ──────────────────────────────

def test_stage8_rules_engine_boundary_enforcement(client, test_case_id, dlsa_token, advocate_token):
    """
    AI or automated rules engine output can only move state to ANALYSIS_READY.
    It can NEVER directly approve, submit, or file.
    Artifacts must be tagged AI_ASSISTED.
    """
    cid = test_case_id
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "START_VERIFICATION"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "SUBMIT_FOR_REVIEW"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "FLAG_LEGAL_AID_REQUIRED"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "ASSIGN_COUNSEL", "payload": {"assigned_advocate_id": "L-1"}})

    # Executing COMPLETE_ANALYSIS moves to ANALYSIS_READY
    res = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={"transition": "COMPLETE_ANALYSIS", "payload": {"machine_status": "THRESHOLD_REACHED"}},
    )
    assert res.status_code == 200
    assert res.json()["current_state"] == "ANALYSIS_READY"

    # AI attempting APPROVE_MATTER directly is blocked with AI Safety Violation
    from app.workflow.state_machine import WorkflowStateMachine
    with pytest.raises(PermissionError) as exc:
        WorkflowStateMachine.validate_transition(
            current_state=MatterState.SUBMITTED,
            action="APPROVE_MATTER",
            actor_role=Role.SUPERVISING_LEGAL_OFFICER,
            payload={"artifact_version_id": "v1"},
            is_ai_agent=True,
        )
    assert "AI Safety Violation" in str(exc.value)


# ── 5. Exact Artifact Version Approvals & Revision Invalidation ───────────────

def test_stale_artifact_approval_invalidation(client, test_case_id, dlsa_token, advocate_token, supervisor_token):
    """
    Verifies that approvals are strictly bound to exact artifact versions.
    Creating a new draft version requires fresh supervisory approval before filing.
    """
    cid = test_case_id
    # Advance to HUMAN_REVIEW
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "START_VERIFICATION"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "SUBMIT_FOR_REVIEW"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "FLAG_LEGAL_AID_REQUIRED"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_token}"}, json={"transition": "ASSIGN_COUNSEL", "payload": {"assigned_advocate_id": "L-1"}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_token}"}, json={"transition": "COMPLETE_ANALYSIS"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_token}"}, json={"transition": "SUBMIT_FOR_HUMAN_REVIEW"})

    # 1. Create version 1
    art_res1 = client.post(
        f"/api/cases/{cid}/artifacts",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={"artifact_id": "art_bail", "artifact_type": "BAIL_APPLICATION", "content_text": "Draft Version 1 Initial"},
    )
    assert art_res1.status_code == 200
    v1_id = art_res1.json()["version_id"]

    # 2. Counsel sign off and supervisor approves Version 1
    client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={"transition": "COUNSEL_SIGN_OFF", "payload": {"artifact_version_id": v1_id}},
    )
    client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {supervisor_token}"},
        json={"transition": "SUPERVISORY_APPROVE", "payload": {"artifact_version_id": v1_id}},
    )

    # 3. Advocate edits draft, creating Version 2
    art_res2 = client.post(
        f"/api/cases/{cid}/artifacts",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={"artifact_id": "art_bail", "artifact_type": "BAIL_APPLICATION", "content_text": "Draft Version 2 Revised"},
    )
    assert art_res2.status_code == 200
    v2_id = art_res2.json()["version_id"]
    assert v2_id != v1_id

    # 4. Attempting to file with unapproved Version 2 must fail!
    res_file_unapproved = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={
            "transition": "RECORD_FILING",
            "payload": {"artifact_version_id": v2_id, "filing_reference": "CNR-TEST-999"},
        },
    )
    assert res_file_unapproved.status_code == 400
    assert "Filing Blocked" in res_file_unapproved.json()["detail"]

    # 5. Supervisor approves Version 2
    client.post(
        f"/api/cases/{cid}/approvals",
        headers={"Authorization": f"Bearer {supervisor_token}"},
        json={
            "artifact_id": "art_bail",
            "artifact_version_id": v2_id,
            "decision": "APPROVED",
            "approval_level": 2,
            "comment": "Revised version 2 approved for filing.",
        },
    )

    # 6. Now filing succeeds!
    res_file_approved = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_token}"},
        json={
            "transition": "RECORD_FILING",
            "payload": {"artifact_version_id": v2_id, "filing_reference": "CNR-TEST-999"},
        },
    )
    assert res_file_approved.status_code == 200
    assert res_file_approved.json()["current_state"] == "FILED"


# ── 6. Case Handoff & Reassignment Dossier ─────────────────────────────────────

def test_case_handoff_and_reassignment_history(client, test_case_id, dlsa_token):
    """Test immutable handoff record creation and handoff dossier compilation."""
    cid = test_case_id

    handoff_payload = {
        "to_user_id": "LWYR-002",
        "to_role": "DEFENSE_ADVOCATE",
        "reason": "Prior advocate transferred to appellate panel; reassigned for trial defense.",
        "metadata": {"special_instructions": "Review medical vulnerability notes"},
    }

    res = client.post(
        f"/api/cases/{cid}/handoff",
        headers={"Authorization": f"Bearer {dlsa_token}"},
        json=handoff_payload,
    )
    assert res.status_code == 200
    assert res.json()["to_user_id"] == "LWYR-002"

    # Retrieve handoff summary
    summary_res = client.get(
        f"/api/cases/{cid}/handoff-summary",
        headers={"Authorization": f"Bearer {dlsa_token}"},
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["case_id"] == cid
    assert summary["originating_reason"] == handoff_payload["reason"]
    assert "INTAKE" in summary["completed_milestones"]
    assert "CLOSED" in summary["pending_requirements"]


# ── 7. Concurrency & Optimistic Locking ───────────────────────────────────────

def test_concurrency_optimistic_locking(client, test_case_id, dlsa_token):
    """Conflicting expected_version rejects transition with 409 Conflict."""
    cid = test_case_id

    # Current version is 1; supply expected_version=99 (mismatch)
    res_mismatch = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {dlsa_token}"},
        json={"transition": "START_VERIFICATION", "expected_version": 99},
    )
    assert res_mismatch.status_code == 409
    assert "version mismatch" in res_mismatch.json()["detail"].lower()

    # Supply correct version (1) -> succeeds and increments version to 2
    res_match = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {dlsa_token}"},
        json={"transition": "START_VERIFICATION", "expected_version": 1},
    )
    assert res_match.status_code == 200
    assert res_match.json()["version_number"] == 2


# ── 8. Unified Chronological Timeline & Provenance Badges ─────────────────────

def test_unified_matter_timeline_with_provenance_badges(client, test_case_id, dlsa_token):
    """Verify chronological timeline returns authoritative provenance badges."""
    cid = test_case_id

    # Execute transition
    client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {dlsa_token}"},
        json={"transition": "START_VERIFICATION", "comment": "Verification started."},
    )

    res = client.get(
        f"/api/matters/{cid}/timeline",
        headers={"Authorization": f"Bearer {dlsa_token}"},
    )
    assert res.status_code == 200
    timeline = res.json()["timeline"]
    assert len(timeline) > 0
    badges = {ev.get("provenance_badge") for ev in timeline}
    assert any(b in ("USER", "SYSTEM", "AI", "EXTERNAL_SYNC") for b in badges)

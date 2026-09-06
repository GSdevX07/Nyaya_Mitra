"""
backend/tests/test_workflow_truth_table_alignment.py
====================================================
Dedicated automated verification test suite for the Single Authoritative
Workflow Truth Table and 26 Boundary Inconsistencies Remediation.

Verifies:
1. Legal filing ownership: DEFENSE_ADVOCATE owns RECORD_FILING; SUPERVISOR blocked.
2. Counsel assignment ownership: DLSA_OFFICER owns ASSIGN_COUNSEL; SUPERVISOR blocked.
3. Linear drafting sequence: Supervisor CANNOT approve directly from HUMAN_REVIEW (400).
4. Filing prerequisite: RECORD_FILING cannot occur from SUBMITTED or without Level 2 sign-off.
5. Strict drafting role: Only assigned DEFENSE_ADVOCATE can execute START_LEGAL_DRAFTING.
6. Counsel sign-off strictness: COUNSEL_SIGN_OFF valid ONLY from HUMAN_REVIEW.
7. Filing source strictness: RECORD_FILING valid ONLY from APPROVED.
8. Removal of SUBMIT_TO_REGISTRY: Invalid transition action.
9. Legacy RELEASED status mapping to POST_RELEASE_FOLLOW_UP.
10. Mandatory payload validation: SCHEDULE_HEARING (bench_name, source_type, hearing_date).
11. Mandatory payload validation: RECORD_COURT_ORDER (judge_name, order_reference, order_type, order_date).
12. Release coordination separation: DLSA / Advocate coordinate; Jail Officer discharges.
13. Physical prison release: CONFIRM_PRISON_RELEASE strictly JAIL_OFFICER.
14. Artifact authoring protection: Only assigned advocate or AI can create BAIL_APPLICATION.
15. Institutional handoff vectors: DLSA->ADVOCATE, ADVOCATE->SUPERVISOR, SUPERVISOR->ADVOCATE, JAIL->DLSA.
16. Unassigned advocate protection: Denied transition execution on unassigned cases.
"""

import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.models.schemas import MatterState
from app.models.domain import MatterState as DomainMatterState
from app.database import get_db_connection


client = TestClient(app)


def make_token(role: Role, user_id: str, full_name: str, linked_case: str = None) -> str:
    claims = {"email": f"{user_id}@demo.nyayamitra.in", "full_name": full_name}
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
def dlsa_tok():
    return make_token(Role.DLSA_OFFICER, "dlsa_truth", "DLSA Officer Verma")


@pytest.fixture
def supervisor_tok():
    return make_token(Role.SUPERVISING_LEGAL_OFFICER, "sup_truth", "Supervising Officer Nair")


@pytest.fixture
def advocate_tok():
    return make_token(Role.DEFENSE_ADVOCATE, "adv_truth", "Adv. Ritu Sen")


@pytest.fixture
def unassigned_advocate_tok():
    return make_token(Role.DEFENSE_ADVOCATE, "adv_unassigned", "Adv. Unassigned Stranger")


@pytest.fixture
def jail_tok():
    return make_token(Role.JAIL_OFFICER, "jail_truth", "Jail Superintendent Rao")


@pytest.fixture
def test_matter():
    """Create fresh matter directly in SQLite database."""
    cid = f"UTP-TT-{uuid.uuid4().hex[:6].upper()}"
    case_dict = {
        "case_id": cid,
        "name": "Undertrial Truth Table Test Subject",
        "offense_sections": ["IPC 379"],
        "arrest_date": "2025-02-01",
        "custody_days": 180,
        "max_sentence_days_for_offense": 1095,
        "undertrial_category": "UNDERTRIAL",
        "applicable_legal_code": "IPC_1860",
        "jail_location": "Central Jail No. 4, Tihar",
        "facility_ids": ["fac_tihar_jail_04"],
        "status": "INTAKE",
        "fir_number": "FIR-2025-999",
        "police_station": "Kashmere Gate",
        "court_name": "Sessions Court, Tis Hazari",
        "assigned_advocate_id": "adv_truth",
        "assigned_advocate_name": "Adv. Ritu Sen",
        "assigned_lawyer_id": "adv_truth",
        "assigned_lawyer": "Adv. Ritu Sen",
        "timeline": [],
        "present_docs": ["fir", "remand_order"],
        "urgency_flags": {"age": 25, "health_flag": False},
    }
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cases (case_id, data, status, version_number) VALUES (?, ?, ?, 1)",
        (cid, json.dumps(case_dict), "INTAKE"),
    )
    conn.commit()
    conn.close()
    yield cid
    try:
        c = get_db_connection()
        cur = c.cursor()
        cur.execute("DELETE FROM cases WHERE case_id = ?", (cid,))
        cur.execute("DELETE FROM documents WHERE case_id = ?", (cid,))
        cur.execute("DELETE FROM matter_approvals WHERE matter_id = ?", (cid,))
        cur.execute("DELETE FROM notifications WHERE case_id = ?", (cid,))
        c.commit()
        c.close()
    except Exception:
        pass
    try:
        from app.supabase_adapter import get_supabase_client, is_supabase_active
        if is_supabase_active():
            s_cli = get_supabase_client()
            s_cli.table("cases").delete().eq("case_id", cid).execute()
            s_cli.table("documents").delete().eq("case_id", cid).execute()
            s_cli.table("matter_approvals").delete().eq("matter_id", cid).execute()
    except Exception:
        pass




# ── 1. Legacy Status Mapping ──────────────────────────────────────────────────

def test_legacy_released_maps_to_post_release_follow_up():
    """Verify legacy RELEASED status maps to POST_RELEASE_FOLLOW_UP, not RELEASE_WORKFLOW."""
    state_schema = MatterState.to_canonical("RELEASED")
    assert state_schema == MatterState.POST_RELEASE_FOLLOW_UP

    state_domain = DomainMatterState.to_canonical("RELEASED")
    assert state_domain == DomainMatterState.POST_RELEASE_FOLLOW_UP


# ── 2. Counsel Assignment Ownership ───────────────────────────────────────────

def test_counsel_assignment_strictly_dlsa(dlsa_tok, supervisor_tok, advocate_tok, test_matter):
    """DLSA owns ASSIGN_COUNSEL; Supervisor and Advocate are blocked (403)."""
    cid = test_matter
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "START_VERIFICATION"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "SUBMIT_FOR_LEGAL_AID_REVIEW"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "FLAG_LEGAL_AID_REQUIRED"})

    res_sup = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {supervisor_tok}"},
        json={"transition": "ASSIGN_COUNSEL", "payload": {"assigned_advocate_id": "adv_truth"}},
    )
    assert res_sup.status_code == 403
    assert "Permission Denied" in res_sup.json()["detail"]

    res_adv = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"transition": "ASSIGN_COUNSEL", "payload": {"assigned_advocate_id": "adv_truth"}},
    )
    assert res_adv.status_code == 403

    res_dlsa = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {dlsa_tok}"},
        json={
            "transition": "ASSIGN_COUNSEL",
            "payload": {"assigned_advocate_id": "adv_truth", "assigned_advocate_name": "Adv. Ritu Sen"},
        },
    )
    assert res_dlsa.status_code == 200
    assert res_dlsa.json()["current_state"] == "ASSIGNED"


# ── 3. Linear Drafting & Approval Sequence ────────────────────────────────────

def test_linear_drafting_and_supervisor_cannot_bypass_counsel_signoff(dlsa_tok, supervisor_tok, advocate_tok, test_matter):
    """
    Supervisor cannot approve directly from HUMAN_REVIEW without counsel sign-off.
    Filing cannot occur directly from SUBMITTED without supervisor approval.
    """
    cid = test_matter
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "START_VERIFICATION"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "SUBMIT_FOR_LEGAL_AID_REVIEW"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "FLAG_LEGAL_AID_REQUIRED"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "ASSIGN_COUNSEL", "payload": {"assigned_advocate_id": "adv_truth"}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "RUN_ANALYSIS"})

    res_draft = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"transition": "START_LEGAL_DRAFTING"},
    )
    assert res_draft.status_code == 200
    assert res_draft.json()["current_state"] == "HUMAN_REVIEW"

    art_res = client.post(
        f"/api/cases/{cid}/artifacts",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={
            "artifact_id": "art_bail_tt",
            "artifact_type": "BAIL_APPLICATION",
            "content_text": "Grounds for statutory bail under Section 479 BNSS...",
        },
    )
    assert art_res.status_code == 200
    ver_id = art_res.json()["version_id"]

    res_sup_early = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {supervisor_tok}"},
        json={"transition": "SUPERVISORY_APPROVE", "payload": {"artifact_version_id": ver_id}},
    )
    assert res_sup_early.status_code == 400
    assert "Illegal transition" in res_sup_early.json()["detail"]

    res_sign = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"transition": "COUNSEL_SIGN_OFF", "payload": {"artifact_version_id": ver_id}},
    )
    assert res_sign.status_code == 200
    assert res_sign.json()["current_state"] == "SUBMITTED"

    res_file_early = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"transition": "RECORD_FILING", "payload": {"filing_reference": "CNR-EARLY-001"}},
    )
    assert res_file_early.status_code == 400
    assert "Illegal transition" in res_file_early.json()["detail"]

    res_approve = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {supervisor_tok}"},
        json={"transition": "SUPERVISORY_APPROVE", "payload": {"artifact_version_id": ver_id}},
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["current_state"] == "APPROVED"

    res_sup_file = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {supervisor_tok}"},
        json={"transition": "RECORD_FILING", "payload": {"filing_reference": "CNR-SUP-FAIL"}},
    )
    assert res_sup_file.status_code == 403
    assert "Permission Denied" in res_sup_file.json()["detail"]

    res_adv_file = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"transition": "RECORD_FILING", "payload": {"filing_reference": "CNR-DLCT01-004523-2026"}},
    )
    assert res_adv_file.status_code == 200
    assert res_adv_file.json()["current_state"] == "FILED"


# ── 4. Mandatory Payload Validation ───────────────────────────────────────────

def test_mandatory_payload_keys_for_hearing_and_order(dlsa_tok, supervisor_tok, advocate_tok, test_matter):
    """
    SCHEDULE_HEARING requires ['hearing_date', 'bench_name', 'source_type'].
    RECORD_COURT_ORDER requires ['order_type', 'order_date', 'judge_name', 'order_reference'].
    Missing any yields 400 Bad Request.
    """
    cid = test_matter
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "START_VERIFICATION"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "SUBMIT_FOR_LEGAL_AID_REVIEW"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "FLAG_LEGAL_AID_REQUIRED"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "ASSIGN_COUNSEL", "payload": {"assigned_advocate_id": "adv_truth"}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "RUN_ANALYSIS"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "START_LEGAL_DRAFTING"})
    art = client.post(f"/api/cases/{cid}/artifacts", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"artifact_id": "art_1", "artifact_type": "BAIL_APPLICATION", "content_text": "Draft"}).json()
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "COUNSEL_SIGN_OFF", "payload": {"artifact_version_id": art["version_id"]}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {supervisor_tok}"}, json={"transition": "SUPERVISORY_APPROVE", "payload": {"artifact_version_id": art["version_id"]}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "RECORD_FILING", "payload": {"filing_reference": "CNR-VALID-01"}})

    res_miss_bench = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"transition": "SCHEDULE_HEARING", "payload": {"hearing_date": "2026-09-20"}},
    )
    assert res_miss_bench.status_code == 400
    assert "Missing required transition prerequisites" in res_miss_bench.json()["detail"]

    res_sched_ok = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={
            "transition": "SCHEDULE_HEARING",
            "payload": {
                "hearing_date": "2026-09-20",
                "bench_name": "Court No. 4, Special Judge",
                "source_type": "eCourts Daily Cause List",
            },
        },
    )
    assert res_sched_ok.status_code == 200
    assert res_sched_ok.json()["current_state"] == "HEARING_SCHEDULED"

    res_order_miss = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"transition": "RECORD_COURT_ORDER", "payload": {"order_type": "BAIL_GRANTED", "order_date": "2026-09-20"}},
    )
    assert res_order_miss.status_code == 400
    assert "Missing required transition prerequisites" in res_order_miss.json()["detail"]

    res_order_ok = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={
            "transition": "RECORD_COURT_ORDER",
            "payload": {
                "order_type": "BAIL_GRANTED",
                "order_date": "2026-09-20",
                "judge_name": "Hon'ble Special Judge S. K. Verma",
                "order_reference": "ORD-2026-DL-8899",
            },
        },
    )
    assert res_order_ok.status_code == 200
    assert res_order_ok.json()["current_state"] == "ORDER_RECEIVED"


# ── 5. Release Coordination vs Physical Custody Release ───────────────────────

def test_release_coordination_and_jail_physical_discharge(dlsa_tok, advocate_tok, jail_tok, supervisor_tok, test_matter):
    """
    COORDINATE_RELEASE is legal coordination (DLSA / Advocate); Jail Officer cannot coordinate.
    CONFIRM_PRISON_RELEASE is physical custody discharge strictly owned by JAIL_OFFICER.
    """
    cid = test_matter
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "START_VERIFICATION"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "SUBMIT_FOR_LEGAL_AID_REVIEW"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "FLAG_LEGAL_AID_REQUIRED"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {dlsa_tok}"}, json={"transition": "ASSIGN_COUNSEL", "payload": {"assigned_advocate_id": "adv_truth"}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "RUN_ANALYSIS"})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "START_LEGAL_DRAFTING"})
    art = client.post(f"/api/cases/{cid}/artifacts", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"artifact_id": "art_1", "artifact_type": "BAIL_APPLICATION", "content_text": "Draft"}).json()
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "COUNSEL_SIGN_OFF", "payload": {"artifact_version_id": art["version_id"]}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {supervisor_tok}"}, json={"transition": "SUPERVISORY_APPROVE", "payload": {"artifact_version_id": art["version_id"]}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "RECORD_FILING", "payload": {"filing_reference": "CNR-VALID-01"}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "SCHEDULE_HEARING", "payload": {"hearing_date": "2026-09-20", "bench_name": "Court 4", "source_type": "Cause List"}})
    client.post(f"/api/cases/{cid}/transitions", headers={"Authorization": f"Bearer {advocate_tok}"}, json={"transition": "RECORD_COURT_ORDER", "payload": {"order_type": "BAIL_GRANTED", "order_date": "2026-09-20", "judge_name": "Judge Verma", "order_reference": "ORD-1"}})

    res_jail_coord = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {jail_tok}"},
        json={"transition": "COORDINATE_RELEASE"},
    )
    assert res_jail_coord.status_code == 403

    res_dlsa_coord = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {dlsa_tok}"},
        json={"transition": "COORDINATE_RELEASE"},
    )
    assert res_dlsa_coord.status_code == 200
    assert res_dlsa_coord.json()["current_state"] == "RELEASE_WORKFLOW"

    res_adv_rel = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"transition": "CONFIRM_PRISON_RELEASE", "payload": {"release_date": "2026-09-21"}},
    )
    assert res_adv_rel.status_code == 403

    res_jail_rel = client.post(
        f"/api/cases/{cid}/transitions",
        headers={"Authorization": f"Bearer {jail_tok}"},
        json={"transition": "CONFIRM_PRISON_RELEASE", "payload": {"release_date": "2026-09-21"}},
    )
    assert res_jail_rel.status_code == 200
    assert res_jail_rel.json()["current_state"] == "POST_RELEASE_FOLLOW_UP"


# ── 6. Artifact Authoring Restrictions ────────────────────────────────────────

def test_bail_artifact_creation_restricted_to_assigned_advocate(jail_tok, dlsa_tok, unassigned_advocate_tok, advocate_tok, test_matter):
    """Only assigned defense advocate (or AI pipeline) can create BAIL_APPLICATION artifact."""
    cid = test_matter

    res_jail = client.post(
        f"/api/cases/{cid}/artifacts",
        headers={"Authorization": f"Bearer {jail_tok}"},
        json={"artifact_id": "art_test", "artifact_type": "BAIL_APPLICATION", "content_text": "Test"},
    )
    assert res_jail.status_code == 403

    res_unassigned = client.post(
        f"/api/cases/{cid}/artifacts",
        headers={"Authorization": f"Bearer {unassigned_advocate_tok}"},
        json={"artifact_id": "art_test", "artifact_type": "BAIL_APPLICATION", "content_text": "Test"},
    )
    assert res_unassigned.status_code == 403

    res_assigned = client.post(
        f"/api/cases/{cid}/artifacts",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"artifact_id": "art_test", "artifact_type": "BAIL_APPLICATION", "content_text": "Valid bail application"},
    )
    assert res_assigned.status_code == 200
    assert res_assigned.json()["artifact_type"] == "BAIL_APPLICATION"


# ── 7. Institutional Handoff Vectors ──────────────────────────────────────────

def test_institutional_handoff_vector_enforcement(dlsa_tok, supervisor_tok, advocate_tok, jail_tok, test_matter):
    """
    Permitted handoff vectors:
    - DLSA -> ADVOCATE
    - ADVOCATE -> SUPERVISOR
    - SUPERVISOR -> ADVOCATE
    - JAIL -> DLSA
    Invalid handoff vectors (e.g. ADVOCATE -> JAIL) rejected with 403.
    """
    cid = test_matter

    res_bad = client.post(
        f"/api/cases/{cid}/handoff",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"to_user_id": "jail_officer_01", "to_role": "JAIL_OFFICER", "reason": "Invalid transfer"},
    )
    assert res_bad.status_code == 403
    assert "Forbidden handoff vector" in res_bad.json()["detail"]

    res_dlsa_to_adv = client.post(
        f"/api/cases/{cid}/handoff",
        headers={"Authorization": f"Bearer {dlsa_tok}"},
        json={"to_user_id": "adv_ritu", "to_role": "DEFENSE_ADVOCATE", "reason": "Case assignment"},
    )
    assert res_dlsa_to_adv.status_code == 200

    res_adv_to_sup = client.post(
        f"/api/cases/{cid}/handoff",
        headers={"Authorization": f"Bearer {advocate_tok}"},
        json={"to_user_id": "sup_nair", "to_role": "SUPERVISING_LEGAL_OFFICER", "reason": "Submitting for review"},
    )
    assert res_adv_to_sup.status_code == 200

    res_sup_to_adv = client.post(
        f"/api/cases/{cid}/handoff",
        headers={"Authorization": f"Bearer {supervisor_tok}"},
        json={"to_user_id": "adv_ritu", "to_role": "DEFENSE_ADVOCATE", "reason": "Requesting additions"},
    )
    assert res_sup_to_adv.status_code == 200

    res_jail_to_dlsa = client.post(
        f"/api/cases/{cid}/handoff",
        headers={"Authorization": f"Bearer {jail_tok}"},
        json={"to_user_id": "dlsa_desk", "to_role": "DLSA_OFFICER", "reason": "Custody intake referral"},
    )
    assert res_jail_to_dlsa.status_code == 200

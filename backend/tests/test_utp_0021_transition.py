"""
test_utp_0021_transition.py - Verification for UTP-0021 Jail Officer Transition
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_db_connection, _MEMORY_CASES
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.models.schemas import CaseState

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    # Reset UTP-0021 to VERIFICATION for isolated test runs
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE cases SET status = 'VERIFICATION' WHERE case_id = 'UTP-0021'")
    cur.execute("UPDATE court_cases SET current_status = 'VERIFICATION' WHERE id = 'UTP-0021'")
    conn.commit()
    conn.close()
    if "UTP-0021" in _MEMORY_CASES:
        _MEMORY_CASES["UTP-0021"].status = CaseState.VERIFICATION
    try:
        from app.supabase_adapter import get_supabase_client, is_supabase_active
        if is_supabase_active():
            sb = get_supabase_client()
            if sb:
                sb.table("cases").update({"status": "VERIFICATION"}).eq("case_id", "UTP-0021").execute()
                sb.table("court_cases").update({"current_status": "VERIFICATION"}).eq("id", "UTP-0021").execute()
    except Exception:
        pass


def test_utp_0021_seeded_and_available_for_jail_officer():
    """Verify UTP-0021 is seeded in SQLite in VERIFICATION state and can be transitioned."""
    jail_token = create_access_token(
        subject="demo_jail",
        role=Role.JAIL_OFFICER.value,
        org_id="org_tihar_jail",
        extra_claims={"facility_ids": ["fac_tihar_jail_04"]}
    )
    headers = {"Authorization": f"Bearer {jail_token}"}

    # 1. State check
    res_state = client.get("/api/cases/UTP-0021/state", headers=headers)
    assert res_state.status_code == 200
    state_data = res_state.json()
    assert state_data["canonical_state"] == "VERIFICATION"

    # 2. Available transitions check
    res_trans = client.get("/api/cases/UTP-0021/available-transitions", headers=headers)
    assert res_trans.status_code == 200
    trans_data = res_trans.json()
    available_actions = [t["action"] for t in trans_data.get("available_transitions", []) if t.get("user_has_permission")]
    assert "SUBMIT_FOR_LEGAL_AID_REVIEW" in available_actions

    # 3. Transition execution
    res_exec = client.post(
        "/api/cases/UTP-0021/transitions",
        headers=headers,
        json={"transition": "SUBMIT_FOR_LEGAL_AID_REVIEW", "comment": "Custody verification completed by Jail Superintendent."},
    )
    assert res_exec.status_code == 200, f"Transition failed: {res_exec.text}"
    exec_data = res_exec.json()
    assert exec_data["current_state"] == "REVIEW"
    assert exec_data["previous_state"] == "VERIFICATION"


def test_utp_0021_resilient_backfill_from_memory():
    """Verify that if SQLite cases table is missing a matter, transition still succeeds via auto-backfill."""
    import uuid
    jail_token = create_access_token(
        subject="demo_jail",
        role=Role.JAIL_OFFICER.value,
        org_id="org_tihar_jail",
        extra_claims={"facility_ids": ["fac_tihar_jail_04"]}
    )
    headers = {"Authorization": f"Bearer {jail_token}"}

    test_cid = f"UTP-BF-{uuid.uuid4().hex[:6].upper()}"
    base_case = _MEMORY_CASES["UTP-0021"]
    clone_case = base_case.model_copy(deep=True)
    clone_case.case_id = test_cid
    clone_case.status = CaseState.VERIFICATION
    _MEMORY_CASES[test_cid] = clone_case

    # Ensure not in SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cases WHERE case_id = ?", (test_cid,))
    conn.commit()
    conn.close()

    # Now execute transition on test_cid - auto-backfill should restore it into SQLite and succeed
    res_exec = client.post(
        f"/api/cases/{test_cid}/transitions",
        headers=headers,
        json={"transition": "SUBMIT_FOR_LEGAL_AID_REVIEW", "comment": "Resilient transition test."},
    )
    assert res_exec.status_code == 200, f"Expected 200 with resilient backfill, got: {res_exec.text}"
    exec_data = res_exec.json()
    assert exec_data["current_state"] == "REVIEW"
    assert exec_data["previous_state"] == "VERIFICATION"

    # Cleanup
    _MEMORY_CASES.pop(test_cid, None)
    try:
        from app.supabase_adapter import get_supabase_client, is_supabase_active
        if is_supabase_active():
            sb = get_supabase_client()
            if sb:
                sb.table("cases").delete().eq("case_id", test_cid).execute()
    except Exception:
        pass


def test_jail_submit_notifies_dlsa_and_persists_state():
    """Verify that SUBMIT_FOR_LEGAL_AID_REVIEW by Jail Officer dispatches urgent notification to DLSA and state sticks."""
    from app.database import get_notifications_for_user, get_case

    jail_token = create_access_token(
        subject="demo_jail",
        role=Role.JAIL_OFFICER.value,
        org_id="org_tihar_jail",
        extra_claims={"facility_ids": ["fac_tihar_jail_04"]}
    )
    dlsa_token = create_access_token(
        subject="demo_dlsa_officer",
        role=Role.DLSA_OFFICER.value,
        org_id="org_dlsa_central",
        extra_claims={"facility_ids": []}
    )
    jail_headers = {"Authorization": f"Bearer {jail_token}"}
    dlsa_headers = {"Authorization": f"Bearer {dlsa_token}"}

    # Execute transition by Jail Officer
    res_exec = client.post(
        "/api/cases/UTP-0021/transitions",
        headers=jail_headers,
        json={"transition": "SUBMIT_FOR_LEGAL_AID_REVIEW", "comment": "Custody records verified, sending to DLSA."},
    )
    assert res_exec.status_code == 200, f"Transition failed: {res_exec.text}"
    exec_data = res_exec.json()
    assert exec_data["current_state"] == "REVIEW"

    # Verify state stuck via multiple queries (simulating page refresh)
    res_state = client.get("/api/cases/UTP-0021/state", headers=jail_headers)
    assert res_state.status_code == 200
    assert res_state.json()["canonical_state"] == "REVIEW"

    case_obj = get_case("UTP-0021")
    assert case_obj is not None
    assert getattr(case_obj, "status").value == "REVIEW"

    # Verify available transitions for Jail Officer no longer shows SUBMIT_FOR_LEGAL_AID_REVIEW
    res_avail_jail = client.get("/api/cases/UTP-0021/available-transitions", headers=jail_headers)
    avail_jail = [t["action"] for t in res_avail_jail.json().get("available_transitions", []) if t.get("user_has_permission")]
    assert "SUBMIT_FOR_LEGAL_AID_REVIEW" not in avail_jail

    # Verify available transitions for DLSA Officer now shows FLAG_LEGAL_AID_REQUIRED
    res_avail_dlsa = client.get("/api/cases/UTP-0021/available-transitions", headers=dlsa_headers)
    avail_dlsa = [t["action"] for t in res_avail_dlsa.json().get("available_transitions", []) if t.get("user_has_permission")]
    assert "FLAG_LEGAL_AID_REQUIRED" in avail_dlsa

    # Verify notification dispatched to DLSA
    notifs = get_notifications_for_user(role="DLSA_OFFICER", user_id="demo_dlsa_officer")
    utp_notifs = [n for n in notifs if n.get("case_id") == "UTP-0021"]
    assert len(utp_notifs) > 0
    assert any("Legal Aid Review Requested" in n.get("title", "") for n in utp_notifs)


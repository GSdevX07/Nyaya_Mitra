import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.database import init_db, get_notifications_for_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def _auth_headers(role: Role, user_id: str = "test_user", linked_case_id: str = None) -> dict:
    claims = {"linked_case_id": linked_case_id} if linked_case_id else None
    token = create_access_token(
        subject=user_id,
        role=role.value,
        org_id="org1",
        extra_claims=claims,
    )
    return {"Authorization": f"Bearer {token}"}


def test_police_officer_sees_only_police_notifications():
    headers = _auth_headers(Role.POLICE_OFFICER, user_id="usr_police_01")
    res = client.get("/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    titles = [n["title"] for n in data]
    
    # Must contain police-specific alerts
    assert any("Remand" in t or "Charge Sheet" in t or "Warrant" in t for t in titles)
    
    # Must NEVER contain advocate-specific or supervisor escalation alerts
    assert not any("Statutory Citation Integrity Escalation" in t for t in titles)
    assert not any("Bail Application Draft Ready" in t for t in titles)

def test_jail_officer_sees_only_jail_notifications():
    headers = _auth_headers(Role.JAIL_OFFICER, user_id="usr_jail_01")
    res = client.get("/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    titles = [n["title"] for n in data]
    
    # Must contain prison superintendent alerts
    assert any("479(2)" in t or "Nominal Roll" in t or "Medical Examination" in t for t in titles)
    assert not any("Remand Period Expiry" in t for t in titles)
    assert not any("Statutory Citation Integrity Escalation" in t for t in titles)

def test_defense_advocate_sees_only_defense_notifications():
    headers = _auth_headers(Role.DEFENSE_ADVOCATE, user_id="usr_adv_01")
    res = client.get("/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    titles = [n["title"] for n in data]
    
    # Must contain advocate alerts
    assert any("Bail Application Draft Ready" in t or "Radar Alert" in t or "Hearing Scheduled" in t for t in titles)
    assert not any("Remand Period Expiry" in t for t in titles)
    assert not any("Nominal Roll & Custody Certificate Due" in t for t in titles)

def test_supervising_legal_officer_sees_escalations():
    headers = _auth_headers(Role.SUPERVISING_LEGAL_OFFICER, user_id="usr_sup_01")
    res = client.get("/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    titles = [n["title"] for n in data]
    
    # Must contain citation escalations and discovered sources
    assert any("Citation Integrity Escalation" in t or "Discovered Legal Source" in t for t in titles)
    assert not any("Remand Period Expiry" in t for t in titles)

def test_accused_user_sees_only_own_case_notifications():
    headers = _auth_headers(Role.ACCUSED_USER, user_id="usr_accused_01", linked_case_id="UTP-0001")
    res = client.get("/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    for n in data:
        if n.get("case_id"):
            assert n["case_id"] == "UTP-0001"
        assert not "Remand Period Expiry" in n["title"]
        assert not "Citation Integrity Escalation" in n["title"]


def test_clear_notifications_flow():
    headers = _auth_headers(Role.POLICE_OFFICER, user_id="usr_police_01")
    # Verify initial notifications exist
    res = client.get("/notifications", headers=headers)
    assert res.status_code == 200
    initial_data = res.json()
    assert len(initial_data) > 0

    # Clear all notifications for this police officer
    del_res = client.delete("/notifications", headers=headers)
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "success"
    assert del_data["cleared_count"] >= len(initial_data)

    # After clearing, get notifications should return empty list for this user
    after_res = client.get("/notifications", headers=headers)
    assert after_res.status_code == 200
    assert len(after_res.json()) == 0


def test_clear_single_notification():
    headers = _auth_headers(Role.JAIL_OFFICER, user_id="usr_jail_01")
    res = client.get("/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    
    target_item = data[0]
    target_id = target_item["id"]
    
    # Delete only that single notification
    del_res = client.delete(f"/notifications?id={target_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["cleared_count"] == 1
    
    # Verify remaining notifications still exist and target is gone
    after_res = client.get("/notifications", headers=headers)
    assert after_res.status_code == 200
    remaining_ids = [n["id"] for n in after_res.json()]
    assert target_id not in remaining_ids
    assert len(remaining_ids) == len(data) - 1

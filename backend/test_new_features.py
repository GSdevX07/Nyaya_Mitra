from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role

client = TestClient(app)

def _get_headers():
    token = create_access_token(
        subject="Legal Officer 104",
        role=Role.DEFENSE_ADVOCATE.value,
        org_id="org_dlsa_central",
    )
    return {"Authorization": f"Bearer {token}"}

def test_available_cases():
    res = client.get("/cases/available", headers=_get_headers())
    print("STATUS:", res.status_code, res.text)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    print(f"Available cases count: {len(data)}")
    if len(data) > 0:
        c = data[0]["case"]
        assert "relative_name" in c
        assert "relative_phone" in c
        assert "permanent_address" in c
        print(f"Case {c['case_id']} relative phone: {c['relative_phone']}")

def test_take_up_case():
    res = client.post("/cases/UTP-0001/take?lawyer_id=Legal%20Officer%20104", headers=_get_headers())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["case"]["assignment_status"] == "ASSIGNED"
    print("Take up case test passed!")

def test_decline_case():
    res = client.post("/cases/UTP-0012/decline?lawyer_id=Legal%20Officer%20104", headers=_get_headers())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "declined"
    print("Decline case test passed!")

def test_lawyer_profile():
    res = client.get("/lawyer/profile", headers=_get_headers())
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "Legal Officer 104"
    assert "bar_association_id" in data
    print(f"Lawyer profile test passed for {data['full_name']}!")

if __name__ == "__main__":
    test_available_cases()
    test_take_up_case()

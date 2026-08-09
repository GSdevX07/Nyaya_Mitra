from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_available_cases():
    res = client.get("/cases/available")
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
    res = client.post("/cases/UTP-0001/take?lawyer_id=Legal%20Officer%20104")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["case"]["assignment_status"] == "ASSIGNED"
    print("Take up case test passed!")

def test_decline_case():
    res = client.post("/cases/UTP-0012/decline?lawyer_id=Legal%20Officer%20104")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "declined"
    print("Decline case test passed!")

def test_lawyer_profile():
    res = client.get("/lawyer/profile")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "Legal Officer 104"
    assert "bar_association_id" in data
    print(f"Lawyer profile test passed for {data['full_name']}!")

if __name__ == "__main__":
    test_available_cases()
    test_take_up_case()
    test_decline_case()
    test_lawyer_profile()
    print("ALL BACKEND NEW FEATURE TESTS PASSED!")

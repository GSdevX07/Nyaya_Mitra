import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.user_store import get_user_by_email

client = TestClient(app)

def _auth_header(email: str) -> dict:
    user = get_user_by_email(email)
    assert user is not None, f"User {email} not found"
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token(
        subject=user.id,
        role=role_val,
        org_id=getattr(user, "org_id", getattr(user, "organization_id", "org_dlsa_central")),
        extra_claims={
            "full_name": user.full_name,
            "district": getattr(user, "district", "Central Delhi"),
            "linked_case_id": getattr(user, "linked_case_id", None),
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_advocate_sign_off_flow():
    # 1. Defense Advocate signs off on UTP-0001
    adv_headers = _auth_header("advocate@demo.nyayamitra.in")
    sign_off_res = client.post(
        "/cases/UTP-0001/sign-off",
        json={"draft_text": "IN THE COURT OF SESSIONS JUDGE AT DELHI\nBAIL PETITION UNDER SECTION 479 BNSS..."},
        headers=adv_headers,
    )
    assert sign_off_res.status_code == 200, sign_off_res.text
    data = sign_off_res.json()
    assert data["status"] == "success"
    assert data["advocate_signed_off"] is True
    assert "signed_off_by" in data
    assert "signed_off_at" in data

    # 2. Verify GET /cases/UTP-0001 returns advocate_signed_off = True
    case_res = client.get("/cases/UTP-0001", headers=adv_headers)
    assert case_res.status_code == 200
    case_data = case_res.json()
    assert case_data.get("advocate_signed_off") is True

    # 3. Verify Unauthorized roles (e.g. Jail Officer) cannot sign off
    jail_headers = _auth_header("jail@demo.nyayamitra.in")
    unauth_res = client.post(
        "/cases/UTP-0001/sign-off",
        json={"draft_text": "Illegal sign-off attempt"},
        headers=jail_headers,
    )
    assert unauth_res.status_code == 403

    # 4. Verify Controlled External Advocate is permitted to sign off on their assigned case
    ext_headers = _auth_header("extadvocate@demo.nyayamitra.in")
    ext_res = client.post(
        "/cases/UTP-0001/sign-off",
        json={"draft_text": "External counsel review sign-off"},
        headers=ext_headers,
    )
    assert ext_res.status_code == 200

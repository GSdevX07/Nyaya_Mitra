"""
test_auth.py — Authentication Unit & Integration Tests for Nyaya Mitra.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token, decode_token
from app.auth.roles import Role
from app.auth.session_store import revoke_token, is_revoked
from app.auth.brute_force import clear_attempts, record_failed_attempt, _ATTEMPTS

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_brute_force():
    """Ensure brute force counters are clean between tests."""
    _ATTEMPTS.clear()
    yield
    _ATTEMPTS.clear()


def test_login_valid_credentials():
    """Test successful login with demo user account."""
    response = client.post(
        "/auth/login",
        json={"email": "dlsa@demo.nyayamitra.in", "password": "Demo@12345"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "DLSA_OFFICER"
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    """Test failed login with incorrect password."""
    response = client.post(
        "/auth/login",
        json={"email": "dlsa@demo.nyayamitra.in", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_brute_force_lockout():
    """Test progressive delay and account lockout after multiple failed attempts."""
    email = "brute_force_victim@demo.nyayamitra.in"
    for _ in range(10):
        record_failed_attempt(email)

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "AnyPassword"},
    )
    assert response.status_code == 429
    assert "Account temporarily locked" in response.json()["detail"]


def test_refresh_token():
    """Test refreshing an access token using a valid refresh token."""
    login_resp = client.post(
        "/auth/login",
        json={"email": "supervisor@demo.nyayamitra.in", "password": "Demo@12345"},
    )
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    assert "access_token" in new_data
    assert new_data["role"] == "SUPERVISING_LEGAL_OFFICER"


def test_logout_and_revocation():
    """Test logging out revokes the access token."""
    login_resp = client.post(
        "/auth/login",
        json={"email": "admin@demo.nyayamitra.in", "password": "Demo@12345"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # /auth/me works before logout
    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200

    # Logout
    logout_resp = client.post("/auth/logout", headers=headers)
    assert logout_resp.status_code == 204

    # /auth/me rejected after logout with 401
    me_after = client.get("/auth/me", headers=headers)
    assert me_after.status_code == 401
    assert "revoked" in me_after.json()["detail"].lower()


def test_demo_token_generation():
    """Test issuing a demo token for a specific role."""
    resp = client.post(
        "/auth/demo-token",
        json={"role": "JAIL_OFFICER"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "JAIL_OFFICER"
    assert "access_token" in data


def test_demo_users_list():
    """Test listing available demo accounts."""
    resp = client.get("/auth/demo-users")
    assert resp.status_code == 200
    data = resp.json()
    assert "demo_users" in data
    assert len(data["demo_users"]) >= 10

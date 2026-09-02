"""
tests/test_accused_citizen_role_remediation.py — Comprehensive Test Suite for Accused Person &
Family Guardian Roles, Citizen Portal API, View Separation, and Database Synchronization.
"""
import os
import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.auth.roles import Role
from app.auth.tokens import create_access_token
from app.database import init_db, DB_PATH
from app.supabase_adapter import assert_production_db_available

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


@pytest.fixture
def accused_token():
    """Generate JWT for demo_accused with linked_case_id UTP-0001."""
    return create_access_token(
        subject="demo_accused",
        role=Role.ACCUSED_USER.value,
        org_id="org_dlsa_central",
        extra_claims={
            "linked_case_id": "UTP-0001",
            "full_name": "Accused Person (Demo)",
            "district": "Central Delhi",
        },
    )


@pytest.fixture
def family_token():
    """Generate JWT for demo_family with linked_case_id UTP-0001."""
    return create_access_token(
        subject="demo_family",
        role=Role.FAMILY_GUARDIAN.value,
        org_id="org_dlsa_central",
        extra_claims={
            "linked_case_id": "UTP-0001",
            "full_name": "Family Guardian (Demo)",
            "district": "Central Delhi",
        },
    )


@pytest.fixture
def unlinked_citizen_token():
    """Generate JWT for a citizen user without any linked_case_id."""
    return create_access_token(
        subject="unlinked_citizen_user",
        role=Role.ACCUSED_USER.value,
        org_id="org_dlsa_central",
        extra_claims={
            "full_name": "Unlinked Citizen",
            "district": "Central Delhi",
        },
    )


# ── 1. Elimination of Silent Fallback to UTP-0001 ──────────────────────────────

def test_unlinked_user_returns_404(unlinked_citizen_token):
    """P0 Issue 1: If user has no linked_case_id, return 404 (NEVER fallback to UTP-0001)."""
    res = client.get("/citizen/my-case", headers={"Authorization": f"Bearer {unlinked_citizen_token}"})
    assert res.status_code == 404, f"Expected 404, got {res.status_code}: {res.text}"
    assert "no active legal aid case" in res.json().get("detail", "").lower()

    # Timeline also returns 404
    tl_res = client.get("/citizen/timeline", headers={"Authorization": f"Bearer {unlinked_citizen_token}"})
    assert tl_res.status_code == 404


# ── 2. View Separation: Accused Self View vs Family Guardian View ──────────────

def test_accused_self_view_permissions(accused_token):
    """P0 Issues 2, 3, 4: Accused Person can view own details including own permanent address."""
    res = client.get("/accused/acc_utp_0001", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data.get("is_accused_self_view") is True
    assert data["id"] == "acc_utp_0001"
    assert "permanent_address" in data
    # Accused can see own address
    assert data["permanent_address"] != "[RESTRICTED - FAMILY GUARDIAN VIEW]"
    # No fake placeholder government identifiers
    gov_ids = data.get("government_identifiers", {})
    assert "CONFIRMED_ON_RECORD" not in str(gov_ids)


def test_family_guardian_view_redactions(family_token):
    """P0 Issues 3, 4: Family Guardian view strictly redacts permanent address and medical details."""
    res = client.get("/accused/acc_utp_0001", headers={"Authorization": f"Bearer {family_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data.get("is_family_guardian_view") is True
    # Permanent address is masked for family guardian
    assert data.get("permanent_address") == "[RESTRICTED - FAMILY GUARDIAN VIEW]"
    # Medical record is completely quarantined
    assert data.get("medical_record") is None
    # No fake placeholder government identifiers
    gov_ids = data.get("government_identifiers", {})
    assert "CONFIRMED_ON_RECORD" not in str(gov_ids)


def test_accused_cannot_access_other_case(accused_token):
    """P1 Issue 18: Accused user is strictly forbidden from accessing another person's dossier."""
    res = client.get("/accused/acc_utp_0007", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 403


# ── 3. Dynamic Citizen Portal & Real Document Visibility ───────────────────────

def test_citizen_view_real_documents(accused_token):
    """P0 Issue 10: Citizen portal returns real verified documents (no hardcoded fake list)."""
    res = client.get("/citizen/my-case", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["case_reference"] == "UTP-0001"
    docs = data.get("available_documents", [])
    assert isinstance(docs, list)
    # Every document in available_documents must be verified
    for d in docs:
        assert d.get("status") in ("VERIFIED", "VERIFIED_PRESENT")
        assert "title" in d


def test_assigned_lawyer_representation(accused_token):
    """P0 Issue 11: Lawyer card accurately reflects assignment status without fake phone or counsel."""
    res = client.get("/citizen/my-case", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    data = res.json()

    lawyer = data.get("assigned_legal_aid_lawyer", {})
    assert "is_assigned" in lawyer
    if lawyer["is_assigned"]:
        assert lawyer.get("name") is not None
        assert lawyer["name"] != "Unassigned"
    else:
        assert lawyer.get("name") is None
        assert "dlsa_helpline" in lawyer


# ── 4. Precise Legal Status Semantics & Procedural Truth ──────────────────────

def test_citizen_status_semantics(accused_token):
    """P0 Issues 6, 7, 8, 9: Status explanations distinguish internal workflow from court/prison actions."""
    res = client.get("/citizen/my-case", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    data = res.json()

    legal_status = data["legal_status"]
    assert "status_code" in legal_status
    assert "title_en" in legal_status
    assert "title_hi" in legal_status
    assert "filing_status" in legal_status

    filing_details = data["filing_details"]
    assert "is_filed" in filing_details
    assert "court_name" in filing_details

    release_details = data["release_details"]
    assert "is_released" in release_details
    assert "release_status" in release_details


# ── 5. Clean Citizen Timeline ──────────────────────────────────────────────────

def test_citizen_timeline_excludes_internal_audit(accused_token):
    """P0 Issue 16, 17: Citizen timeline excludes internal audit logs and security telemetry."""
    res = client.get("/citizen/timeline", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    timeline = res.json()
    assert isinstance(timeline, list)

    for item in timeline:
        # Must not contain audit events
        assert "Audit:" not in item.get("title", "")
        assert item.get("category") not in ("EVIDENCE_INTEGRITY", "SECURITY_ALERT", "SYSTEM_INTERNAL")
        # Must have plain language title and date
        assert "title" in item
        assert "event_date" in item


# ── 6. Database Synchronization & Production Assertions ───────────────────────

def test_production_database_unavailable_assertion(monkeypatch):
    """P0 Database 7: In production, assert_production_db_available raises 503 if Supabase is down."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr("app.supabase_adapter.is_supabase_active", lambda: False)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        assert_production_db_available()
    assert exc_info.value.status_code == 503
    assert "authoritative postgresql database is currently unavailable" in str(exc_info.value.detail).lower()

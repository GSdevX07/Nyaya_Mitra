"""
tests/test_stage11_accused_family_experience.py — Stage 11 Test Suite.
======================================================================
Verifies:
1. Mobile-first constrained citizen overview payload & 404 unlinked handling.
2. Mandatory statutory disclaimer on AI explanations (no definitive bail promises).
3. Configurable multi-language service with authoritative English & derived display.
4. Missing citizen documents list with submission instructions.
5. Entitled documents with low-bandwidth text summaries (zero confidential leaks).
6. Citizen action requests routing to DLSA Task Queue.
7. Notification preferences & statutory consent registry.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.roles import Role
from app.auth.tokens import create_access_token
from app.database import init_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


@pytest.fixture
def accused_token():
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
def unlinked_token():
    return create_access_token(
        subject="unlinked_citizen",
        role=Role.ACCUSED_USER.value,
        org_id="org_dlsa_central",
        extra_claims={
            "full_name": "Unlinked Citizen",
            "district": "Central Delhi",
        },
    )


# ── 1. Unlinked User Handling ────────────────────────────────────────────────

def test_unlinked_user_overview_returns_404(unlinked_token):
    res = client.get("/citizen/overview", headers={"Authorization": f"Bearer {unlinked_token}"})
    assert res.status_code == 404
    assert "no active legal aid case" in res.json()["detail"].lower()


# ── 2. Accused Overview & Authorized References ───────────────────────────────

def test_accused_overview_payload(accused_token):
    res = client.get("/citizen/overview", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["portal_mode"] == "ACCUSED_USER"
    assert data["case_reference"] == "UTP-0001"
    assert "court_name" in data
    assert "police_station" in data
    assert "current_known_status" in data
    assert "filing_details" in data
    assert "release_details" in data
    assert len(data["upcoming_known_events"]) >= 1
    assert data["support_helpline"] == "15100"


# ── 3. Family Guardian View Separation ────────────────────────────────────────

def test_family_guardian_overview_mode(family_token):
    res = client.get("/citizen/overview", headers={"Authorization": f"Bearer {family_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["portal_mode"] == "FAMILY_GUARDIAN"
    assert data["case_reference"] == "UTP-0001"
    # Zero internal risk scores or unlinked case leaks
    assert "risk_score" not in str(data)
    assert "advocate_private_notes" not in str(data)


# ── 4. AI Explanation Mandatory Statutory Disclaimer ─────────────────────────

def test_ai_explanation_statutory_disclaimer(accused_token):
    res = client.get("/citizen/overview", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    ai_expl = res.json()["ai_procedural_explanation"]

    assert ai_expl["is_ai_generated"] is True
    assert ai_expl["disclaimer_label"] == "AI Procedural Explanation — Not a Legal Decision"
    assert "not a court order" in ai_expl["disclaimer_text"].lower()
    assert "never promises release" in ai_expl["disclaimer_text"].lower() or "never guarantees" in ai_expl["disclaimer_text"].lower()
    # Confirm explanation never promises release
    assert "definitely release" not in ai_expl["explanation_text"].lower()
    assert "guarantee bail" not in ai_expl["explanation_text"].lower()


# ── 5. Multi-Language Service & Derived Display ──────────────────────────────

def test_multilingual_overview_derived_display(accused_token):
    # Fetch Hindi overview
    res_hi = client.get("/citizen/overview?lang=hi", headers={"Authorization": f"Bearer {accused_token}"})
    assert res_hi.status_code == 200
    data_hi = res_hi.json()

    assert data_hi["language_meta"]["current_language"] == "hi"
    assert data_hi["language_meta"]["is_derived_display"] is True
    assert data_hi["language_meta"]["authoritative_language"] == "en"
    assert "derived display" in data_hi["language_meta"]["disclaimer"].lower()

    # Authoritative English text must be preserved
    assert data_hi["current_known_status"]["is_derived"] is True
    assert data_hi["current_known_status"]["authoritative_title"] != ""
    assert data_hi["ai_procedural_explanation"]["authoritative_english_text"] != ""


def test_supported_languages_list(accused_token):
    res = client.get("/citizen/languages", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    langs = res.json()
    codes = {l["code"] for l in langs}
    assert {"en", "hi", "kn", "te", "ta", "mr", "bn"}.issubset(codes)
    en_lang = next(l for l in langs if l["code"] == "en")
    assert en_lang["is_authoritative"] is True


# ── 6. Missing Documents From Citizen Side ────────────────────────────────────

def test_missing_documents_from_citizen(accused_token):
    res = client.get("/citizen/overview", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    missing = res.json()["missing_documents_from_citizen"]
    assert len(missing) >= 1
    doc_types = {m["document_type"] for m in missing}
    # Local surety proof must be present
    assert "surety_identity_proof" in doc_types
    for m in missing:
        assert m["why_needed"] != ""
        assert m["how_to_submit"] != ""


# ── 7. Approved Entitled Documents & Low-Bandwidth Text Summaries ─────────────

def test_approved_entitled_documents(accused_token):
    res = client.get("/citizen/documents", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) >= 1
    for d in docs:
        assert d["is_approved_for_citizen"] is True
        assert d["text_summary"] != ""
        assert d["file_size_formatted"] != ""


def test_document_summary_endpoint(accused_token):
    res = client.get("/citizen/documents/doc_UTP-0001_remand_order/summary", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    doc_summary = res.json()
    assert "text_preview" in doc_summary
    assert doc_summary["status"] == "VERIFIED"


# ── 8. Citizen Action Requests & DLSA Task Queue Routing ──────────────────────

def test_submit_citizen_action_request(accused_token):
    payload = {
        "request_type": "FLAG_INCORRECT_INFO",
        "subject": "Correction of Father Name in Remand Sheet",
        "details": "The father name in the remand record contains a spelling discrepancy compared to the family ration card.",
        "discrepancy_field": "father_name",
    }
    res = client.post("/citizen/requests", json=payload, headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    req = res.json()
    assert req["id"].startswith("REQ-")
    assert req["status"] == "SUBMITTED"
    assert req["task_id"].startswith("TASK-CITIZEN-")

    # Verify task exists in task queue
    from app.services.task_service import get_task_repository
    task_repo = get_task_repository()
    task = task_repo.get_task_by_id(req["task_id"])
    assert task is not None
    assert task["task_type"] == "CITIZEN_REQUEST_REVIEW"
    assert task["owner_role"] == "DLSA_OFFICER"
    assert task["priority"] == "HIGH"


def test_list_citizen_requests(accused_token):
    res = client.get("/citizen/requests", headers={"Authorization": f"Bearer {accused_token}"})
    assert res.status_code == 200
    requests = res.json()
    assert len(requests) >= 1
    assert requests[0]["request_type"] in ("FLAG_INCORRECT_INFO", "REQUEST_HELP", "REQUEST_DOCUMENT_COPY", "REQUEST_DLSA_CONTACT")


# ── 9. Notification Preferences & Consent Record ─────────────────────────────

def test_notification_preferences_get_and_update(accused_token):
    # 1. Get initial preferences
    res_get = client.get("/citizen/notification-preferences", headers={"Authorization": f"Bearer {accused_token}"})
    assert res_get.status_code == 200
    prefs = res_get.json()
    assert prefs["consent_status"] == "OPTED_IN"
    assert prefs["consent_version"] != ""

    # 2. Update preferences
    update_payload = {
        "phone_number": "+91 98123 45678",
        "channel_sms_enabled": True,
        "channel_whatsapp_enabled": True,
        "channel_in_app_enabled": True,
        "preferred_language": "hi",
        "consent_status": "OPTED_IN",
        "consent_text": "I consent to receive case status updates and legal-aid notices under the Legal Services Authorities Act, 1987.",
    }
    res_post = client.post("/citizen/notification-preferences", json=update_payload, headers={"Authorization": f"Bearer {accused_token}"})
    assert res_post.status_code == 200
    updated = res_post.json()
    assert updated["phone_number"] == "+91 98123 45678"
    assert updated["preferred_language"] == "hi"
    assert updated["consent_status"] == "OPTED_IN"
    assert updated["consent_timestamp"] != ""

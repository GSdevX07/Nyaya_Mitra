"""
test_endpoints.py - Automated Unit & Integration Tests for Nyaya Mitra API.
Verifies all 6 canonical hero cases, Section 479 BNSS Rule Engine, and FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_all_cases, get_case
from app.agents.eligibility_agent import evaluate_eligibility
from app.agents.orchestrator import process_case
from app.models.schemas import CaseRecord, PrisonerCategory, LegalCode, CaseState

from app.auth.tokens import create_access_token
from app.auth.roles import Role

client = TestClient(app)

_admin_token = create_access_token(
    subject="test_admin_hero",
    role=Role.PLATFORM_ADMIN.value,
    org_id="org_dlsa_central",
)
AUTH_HEADERS = {"Authorization": f"Bearer {_admin_token}"}


def setup_module():
    """Ensure database is seeded with the 6 canonical hero cases."""
    init_db()


def test_health_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["total_cases_in_db"] >= 6


def test_cases_list_and_sorting():
    response = client.get("/cases", headers=AUTH_HEADERS)
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) >= 6
    # Verify sorted by urgency_score descending
    scores = [c["urgency_score"] for c in cases]
    assert scores == sorted(scores, reverse=True)


def test_hero_case_1_standard_undertrial():
    """UTP-0001: BNS 115(2), first-time, all docs present, custody=200/365d -> Eligible."""
    case = get_case("UTP-0001")
    assert case is not None
    assert case.legal_code == LegalCode.BNS_2023
    assert case.prisoner_category == PrisonerCategory.UNDERTRIAL
    
    result = evaluate_eligibility(case)
    assert result["eligible"] is True
    assert result["required_custody_days"] == 122  # ceil(365 * 1/3)
    assert result["countable_custody_days"] == 200
    assert result["days_overdue"] == 78


def test_hero_case_2_urgent_medical_undertrial():
    """UTP-0007: BNS 303(2), 63 yrs + health flag, custody=410/730d -> High Urgency."""
    case = get_case("UTP-0007")
    assert case is not None
    assert case.urgency_flags.age == 63
    assert case.urgency_flags.health_flag is True
    
    orch = process_case(case)
    assert orch["eligibility"]["eligible"] is True
    assert orch["completeness"]["is_complete"] is True
    assert orch["draft_ready"] is True
    assert orch["urgency_score"] > 200


def test_hero_case_3_missing_documents_blocker():
    """UTP-0015: IPC 392, missing charge_sheet -> Drafting blocked."""
    case = get_case("UTP-0015")
    assert case is not None
    assert case.legal_code == LegalCode.IPC_1860
    assert "charge_sheet" not in case.present_docs
    
    orch = process_case(case)
    assert orch["eligibility"]["eligible"] is True
    assert orch["completeness"]["is_complete"] is False
    assert orch["draft_ready"] is False  # Blocked by missing document


def test_hero_case_4_life_imprisonment_multi_case_exclusion():
    """UTP-0012: IPC 302 / multiple active cases -> Excluded / Human Review Required."""
    case = get_case("UTP-0012")
    assert case is not None
    assert case.punishable_by_death_or_life is True
    
    result = evaluate_eligibility(case)
    assert result["eligible"] is False
    assert result["human_review_required"] is True
    assert "STATUTORY_EXCLUSION" in result["legal_basis"]


def test_hero_case_5_convicted_prisoner_appeal():
    """CONV-0101: BNS 105, convicted, judgment available -> Appeal Pending."""
    case = get_case("CONV-0101")
    assert case is not None
    assert case.prisoner_category == PrisonerCategory.CONVICTED
    assert case.appeal_details is not None
    assert "High Court" in case.appeal_details.appellate_forum


def test_hero_case_6_post_release_preserved():
    """REL-0042: IPC 420, bail granted and released -> Post-Release Preserved."""
    case = get_case("REL-0042")
    assert case is not None
    assert case.status == CaseState.POST_RELEASE_PRESERVED
    assert case.post_release_details is not None


def test_stakeholders_overview_endpoint():
    response = client.get("/stakeholders/overview", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "jail_view" in data
    assert "dlsa_view" in data
    assert "slsa_view" in data
    assert "advocate_view" in data


def test_human_approval_and_filing_lifecycle():
    """Test explicit transition: REVIEW -> APPROVED_READY_FOR_FILING -> FILED."""
    appr_res = client.post("/cases/UTP-0001/approve?lawyer_id=Adv.%20Sharma", headers=AUTH_HEADERS)
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED_READY_FOR_FILING"

    file_res = client.post("/cases/UTP-0001/file?filing_reference=EC-DEL-2025-001", headers=AUTH_HEADERS)
    assert file_res.status_code == 200
    assert file_res.json()["status"] == "FILED"

    timeline_res = client.get("/cases/UTP-0001/timeline", headers=AUTH_HEADERS)
    assert timeline_res.status_code == 200
    events = timeline_res.json()["timeline"]
    assert any(e["event_type"] == "FILING" for e in events)


def test_evidence_integrity_verification():
    response = client.get("/evidence", headers=AUTH_HEADERS)
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    evi_id = items[0]["id"]
    verify_res = client.post(f"/evidence/verify?evidence_id={evi_id}", headers=AUTH_HEADERS)
    assert verify_res.status_code == 200
    assert "status" in verify_res.json()

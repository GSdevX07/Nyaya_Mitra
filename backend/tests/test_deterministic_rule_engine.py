"""
test_deterministic_rule_engine.py
=================================
Exhaustive verification of Stage 8 Deterministic Legal Rules Framework:
- Pure Python arithmetic (zero LLM calculation)
- Exact, just-below, and just-above statutory threshold boundaries
- 1/3 First-Time Offender Proviso with documented math.ceil rounding
- Missing input handling (refusal to silently guess zero or false)
- Conflicting authoritative institutional records (reconciliation required)
- Section 479(1) Proviso 2 (Capital & Life Imprisonment Exclusions)
- Section 479(1) Proviso 3 (Multiple Pending Cases)
- Accused-attributable delay deductions
- Convicted prisoner routing to appellate assistance
- Rule lifecycle governance & strict legal authority RBAC (Platform Admin barred)
- Historical rule-version reproducibility
- Structured explanation object integrity
"""

import math
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.roles import Role
from app.auth.tokens import create_access_token
from app.rules.models import RuleMachineStatus, RuleLifecycleState
from app.rules.service import _GLOBAL_SERVICE as rule_service
from app.rules.bnss_479_engine import evaluate_bnss_479_detention

client = TestClient(app)


def _token(role: Role, user_id: str = "u_test", extra: dict = None) -> dict:
    claims = extra or {}
    tok = create_access_token(
        subject=user_id,
        role=role.value,
        org_id="org_dlsa_central",
        extra_claims=claims,
    )
    return {"Authorization": f"Bearer {tok}"}


class MockCase:
    """Mock CaseRecord proxy for deterministic testing."""
    def __init__(
        self,
        case_id="UTP-TEST",
        custody_days=120,
        excluded_delay_days=0,
        max_sentence_days=360,
        repeat_offender=False,
        punishable_by_death_or_life=False,
        multiple_active_cases=False,
        prisoner_category="UNDERTRIAL",
        offense_sections=None,
        missing_docs=None,
        conflicting_records=None,
    ):
        self.case_id = case_id
        self.custody_days = custody_days
        self.excluded_delay_days = excluded_delay_days
        self.max_sentence_days_for_offense = max_sentence_days
        self.punishable_by_death_or_life = punishable_by_death_or_life
        self.multiple_active_cases = multiple_active_cases
        self.prisoner_category = prisoner_category
        self.offense_sections = offense_sections or ["BNS Section 303(2)"]
        self.missing_docs = missing_docs or []
        self.conflicting_records = conflicting_records or []

        class MockFlags:
            def __init__(self, rep):
                self.repeat_offender = rep
        self.urgency_flags = MockFlags(repeat_offender)
        self.field_provenance = {}


# ── Test 1: Exact Threshold Boundary ──────────────────────────────────────────
def test_exact_threshold_boundary():
    """Case with max sentence 360 days and 1/3 fraction needs exactly 120 days."""
    case = MockCase(custody_days=120, max_sentence_days=360, repeat_offender=False)
    res = rule_service.evaluate_case(case)
    assert res.machine_status == RuleMachineStatus.THRESHOLD_REACHED
    assert res.is_eligible is True
    assert res.threshold_days == 120
    assert res.countable_custody_days == 120
    assert res.days_overdue == 0


# ── Test 2: Just Below Threshold Boundary ─────────────────────────────────────
def test_just_below_threshold_boundary():
    """119 days served when 120 required -> THRESHOLD_NOT_REACHED."""
    case = MockCase(custody_days=119, max_sentence_days=360, repeat_offender=False)
    res = rule_service.evaluate_case(case)
    assert res.machine_status in (RuleMachineStatus.THRESHOLD_NOT_REACHED, RuleMachineStatus.POTENTIALLY_APPLICABLE)
    assert res.is_eligible is False
    assert res.days_overdue == 0
    assert "1 additional countable detention days required" in res.explanation.explanation_text


# ── Test 3: Just Above Threshold Boundary ─────────────────────────────────────
def test_just_above_threshold_boundary():
    """121 days served when 120 required -> THRESHOLD_REACHED with 1 day overdue."""
    case = MockCase(custody_days=121, max_sentence_days=360, repeat_offender=False)
    res = rule_service.evaluate_case(case)
    assert res.machine_status == RuleMachineStatus.THRESHOLD_REACHED
    assert res.is_eligible is True
    assert res.days_overdue == 1


# ── Test 4: One-Third First-Time Offender with math.ceil Rounding ─────────────
def test_one_third_first_time_offender_math_ceil_rounding():
    """365 days max sentence at 1/3 = 121.666... Documented ceiling = 122 days."""
    case = MockCase(custody_days=121, max_sentence_days=365, repeat_offender=False)
    res = rule_service.evaluate_case(case)
    assert res.threshold_days == 122
    assert res.is_eligible is False

    # Once 122 days reached:
    case_met = MockCase(custody_days=122, max_sentence_days=365, repeat_offender=False)
    res_met = rule_service.evaluate_case(case_met)
    assert res_met.is_eligible is True
    assert res_met.machine_status == RuleMachineStatus.THRESHOLD_REACHED


# ── Test 5: Repeat Offender Threshold (1/2 Maximum Punishment) ────────────────
def test_repeat_offender_threshold_half():
    """Repeat offender requires 1/2 of 360 = 180 days (not 120 days)."""
    case = MockCase(custody_days=140, max_sentence_days=360, repeat_offender=True)
    res = rule_service.evaluate_case(case)
    assert res.threshold_days == 180
    assert res.is_eligible is False

    case_served = MockCase(custody_days=180, max_sentence_days=360, repeat_offender=True)
    res_served = rule_service.evaluate_case(case_served)
    assert res_served.is_eligible is True
    assert res_served.machine_status == RuleMachineStatus.THRESHOLD_REACHED


# ── Test 6: Missing Custody Duration Refuses to Fabricate Zero ─────────────────
def test_missing_custody_duration_returns_insufficient_data():
    """Missing custody_days returns INSUFFICIENT_DATA, never assuming 0 or eligible."""
    case = MockCase(custody_days=None, max_sentence_days=360, repeat_offender=False)
    res = rule_service.evaluate_case(case)
    assert res.machine_status == RuleMachineStatus.INSUFFICIENT_DATA
    assert res.is_eligible is False
    assert any(f["field"] == "custody_days" for f in res.explanation.missing_or_conflicting_inputs)


# ── Test 7: Missing Maximum Sentence Refuses to Fabricate Truth ────────────────
def test_missing_max_sentence_returns_insufficient_data():
    """Missing or 0 max_sentence returns INSUFFICIENT_DATA."""
    case = MockCase(custody_days=120, max_sentence_days=None, repeat_offender=False)
    res = rule_service.evaluate_case(case)
    assert res.machine_status == RuleMachineStatus.INSUFFICIENT_DATA
    assert res.is_eligible is False
    assert any(f["field"] == "max_sentence_days_for_offense" for f in res.explanation.missing_or_conflicting_inputs)


# ── Test 8: Missing Repeat Offender Status ────────────────────────────────────
def test_missing_repeat_offender_status_returns_insufficient_data():
    """Unrecorded prior conviction status returns INSUFFICIENT_DATA."""
    case = MockCase(custody_days=120, max_sentence_days=360, repeat_offender=None)
    res = rule_service.evaluate_case(case)
    assert res.machine_status == RuleMachineStatus.INSUFFICIENT_DATA
    assert any(f["field"] == "repeat_offender" for f in res.explanation.missing_or_conflicting_inputs)


# ── Test 9: Conflicting Authoritative Institutional Records ───────────────────
def test_conflicting_authoritative_records_triggers_manual_review():
    """Discrepancy between jail custody register and police arrest sheet returns MANUAL_REVIEW."""
    conflicts = [{
        "field": "arrest_and_admission_dates",
        "source_a": "Central Jail Custody Register (Admission: 2024-03-01)",
        "source_b": "Police Arrest Memo (Arrest: 2024-02-15)",
        "details": "15 days untracked gap between police custody and jail intake.",
    }]
    case = MockCase(custody_days=150, max_sentence_days=360, conflicting_records=conflicts)
    res = rule_service.evaluate_case(case)
    assert res.machine_status == RuleMachineStatus.MANUAL_REVIEW
    assert res.is_eligible is False
    assert "Conflicting authoritative records" in res.explanation.explanation_text
    assert len(res.explanation.missing_or_conflicting_inputs) > 0


# ── Test 10: Section 479(1) Proviso 2 (Death / Life Imprisonment Exclusion) ────
def test_statutory_exclusion_death_or_life():
    """Offenses punishable by death or life imprisonment are EXCLUDED."""
    case = MockCase(custody_days=500, max_sentence_days=1000, punishable_by_death_or_life=True)
    res = rule_service.evaluate_case(case)
    assert res.machine_status == RuleMachineStatus.EXCLUDED
    assert res.is_eligible is False
    assert "STATUTORY EXCLUSION" in res.explanation.explanation_text


# ── Test 11: Section 479(1) Proviso 3 (Multiple Pending Cases) ────────────────
def test_statutory_proviso_multiple_active_cases():
    """Multiple pending trials trigger MANUAL_REVIEW under Section 479(1) Proviso 3."""
    case = MockCase(custody_days=200, max_sentence_days=360, multiple_active_cases=True)
    res = rule_service.evaluate_case(case)
    assert res.machine_status == RuleMachineStatus.MANUAL_REVIEW
    assert res.is_eligible is False
    assert "Section 479(1) Proviso 3" in res.explanation.explanation_text


# ── Test 12: Accused-Attributable Delay Deduction ─────────────────────────────
def test_accused_attributable_delay_deduction():
    """Total 150 days elapsed, but 40 days delay caused by accused -> 110 countable days."""
    # Threshold is 120 days. 150 elapsed - 40 delay = 110 countable (below 120 required)
    case = MockCase(custody_days=150, excluded_delay_days=40, max_sentence_days=360)
    res = rule_service.evaluate_case(case)
    assert res.countable_custody_days == 110
    assert res.is_eligible is False

    # If elapsed is 170 days: 170 - 40 = 130 countable (above 120 required)
    case_met = MockCase(custody_days=170, excluded_delay_days=40, max_sentence_days=360)
    res_met = rule_service.evaluate_case(case_met)
    assert res_met.countable_custody_days == 130
    assert res_met.is_eligible is True


# ── Test 13: Mandatory Document Blocker ───────────────────────────────────────
def test_missing_mandatory_court_records_blocks_eligibility():
    """Missing remand order prevents automatic eligibility filing."""
    case = MockCase(custody_days=150, max_sentence_days=360, missing_docs=["Remand Order Copy"])
    res = rule_service.evaluate_case(case)
    # Threshold reached mathematically, but flagged as POTENTIALLY_APPLICABLE due to doc blocker
    assert res.is_eligible is False
    assert res.machine_status == RuleMachineStatus.POTENTIALLY_APPLICABLE
    assert "Mandatory records missing" in res.explanation.manual_review_reason


# ── Test 14: Convicted Prisoner Routing to Appellate Workflow ─────────────────
def test_convicted_prisoner_routed_to_appellate():
    """Convicted prisoner triggers MANUAL_REVIEW directing to Section 389 appeal."""
    case = MockCase(custody_days=300, max_sentence_days=360, prisoner_category="CONVICTED")
    res = rule_service.evaluate_case(case)
    assert res.machine_status == RuleMachineStatus.MANUAL_REVIEW
    assert "Appellate Legal Aid" in res.explanation.explanation_text


# ── Test 15: Maximum Detention Ceiling ────────────────────────────────────────
def test_maximum_detention_ceiling_reached():
    """Custody duration reaching or exceeding total maximum imprisonment."""
    case = MockCase(custody_days=365, max_sentence_days=360)
    res = rule_service.evaluate_case(case)
    assert "MAXIMUM STATUTORY DETENTION CEILING REACHED" in res.explanation.explanation_text
    assert res.machine_status == RuleMachineStatus.THRESHOLD_REACHED


# ── Test 16: Historical Rule-Version Reproducibility ──────────────────────────
def test_historical_rule_version_reproducibility():
    """Historical rule comparison: CRPC 436A vs BNSS 479 produces different fractions."""
    case = MockCase(custody_days=130, max_sentence_days=360, repeat_offender=False)
    
    # Under BNSS 479 (1/3 = 120d): Eligible
    bnss_res = rule_service.evaluate_case(case, rule_version="BNSS_479_RULESET_V1_2023")
    assert bnss_res.is_eligible is True
    assert bnss_res.threshold_days == 120

    # Under CRPC 436A (1/2 = 180d): Ineligible
    crpc_res = rule_service.evaluate_case(case, rule_version="CRPC_436A_RULESET_V1_1973")
    assert crpc_res.threshold_days == 180
    assert crpc_res.is_eligible is False


# ── Test 17: Reconstructing Past Assessment via Execution Record ──────────────
def test_reconstruct_past_assessment():
    """Assessments can be reconstructed from their execution ID."""
    case = MockCase(custody_days=125, max_sentence_days=360)
    res = rule_service.evaluate_case(case)
    exec_id = res.execution_id

    reconstructed = rule_service.reconstruct_assessment(exec_id)
    assert reconstructed is not None
    assert reconstructed["execution_id"] == exec_id
    assert reconstructed["machine_status"] == RuleMachineStatus.THRESHOLD_REACHED.value
    assert reconstructed["input_snapshot"]["custody_days"] == 125


# ── Test 18: API Endpoint GET /rules ──────────────────────────────────────────
def test_api_list_rules():
    """Authenticated institutional users can inspect statutory rules."""
    headers = _token(Role.DLSA_OFFICER)
    resp = client.get("/rules", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "rules" in data
    assert any(r["rule_id"] == "RULE-BNSS-479-THRESHOLD-V1" for r in data["rules"])


# ── Test 19: API Endpoint POST /rules/{rule_id}/evaluate ──────────────────────
def test_api_evaluate_rule_against_facts():
    """Direct ad-hoc evaluation endpoint returns structured explanation object."""
    headers = _token(Role.DEFENSE_ADVOCATE)
    payload = {
        "case_id": "ADHOC-001",
        "custody_days": 135,
        "max_sentence_days": 365,
        "repeat_offender": False,
        "punishable_by_death_or_life": False,
        "multiple_active_cases": False,
    }
    resp = client.post("/rules/RULE-BNSS-479-THRESHOLD-V1/evaluate", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["machine_status"] == "THRESHOLD_REACHED"
    assert data["is_eligible"] is True
    assert "explanation" in data
    assert data["explanation"]["calculation_performed"]["threshold_days"] == 122


# ── Test 20: Governance RBAC - Platform Admin Barred from Approving Rules ─────
def test_platform_admin_barred_from_approving_legal_rules():
    """Platform Administrators are strictly barred from approving statutory rules."""
    headers = _token(Role.PLATFORM_ADMIN, user_id="demo_admin")
    resp = client.post(
        "/rules/RULE-BNSS-479-THRESHOLD-V1/lifecycle",
        json={"target_state": "APPROVED", "notes": "Admin attempt"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "SUPERVISING_LEGAL_OFFICER" in resp.json()["detail"]


# ── Test 21: Governance RBAC - Supervising Legal Officer Authorized to Approve ─
def test_supervising_legal_officer_authorized_for_lifecycle():
    """Supervising Legal Officer has institutional authority for rule lifecycle transitions."""
    import uuid
    from app.rules.models import LegalRuleDefinition, RuleCategory, RuleLifecycleState

    # 1. Register a test rule in DRAFT state
    rule_id = f"RULE-TEST-{uuid.uuid4().hex[:6].upper()}"
    draft_rule = LegalRuleDefinition(
        rule_id=rule_id,
        rule_version=f"TEST_VERSION_{uuid.uuid4().hex[:4].upper()}",
        title="Test Operational Statutory Rule",
        category=RuleCategory.LEGAL_AID_OPERATIONAL_DEADLINES,
        statutory_source="NALSA SOP 2024",
        effective_date="2024-07-01",
        lifecycle_state=RuleLifecycleState.DRAFT,
        calculation_method="direct",
        explanation_template="Test rule template",
    )
    rule_service.registry.register_rule(draft_rule, persist=True)

    headers = _token(Role.SUPERVISING_LEGAL_OFFICER, user_id="demo_supervisor")

    # 2. Transition DRAFT -> LEGAL_REVIEW
    resp_review = client.post(
        f"/rules/{rule_id}/lifecycle",
        json={"target_state": "LEGAL_REVIEW", "notes": "Under formal legal review"},
        headers=headers,
    )
    assert resp_review.status_code == 200
    assert resp_review.json()["rule"]["lifecycle_state"] == "LEGAL_REVIEW"

    # 3. Transition LEGAL_REVIEW -> APPROVED
    resp_app = client.post(
        f"/rules/{rule_id}/lifecycle",
        json={"target_state": "APPROVED", "notes": "Approved by supervising legal officer"},
        headers=headers,
    )
    assert resp_app.status_code == 200
    assert resp_app.json()["rule"]["lifecycle_state"] == "APPROVED"

    # 4. Transition APPROVED -> ACTIVE
    resp_act = client.post(
        f"/rules/{rule_id}/lifecycle",
        json={"target_state": "ACTIVE", "notes": "Enacted as active rule"},
        headers=headers,
    )
    assert resp_act.status_code == 200
    assert resp_act.json()["rule"]["lifecycle_state"] == "ACTIVE"


# ── Test 22: Backward Compatibility of evaluate_eligibility() ─────────────────
def test_evaluate_eligibility_backward_compatibility():
    """Ensure evaluate_eligibility() returns all expected legacy keys plus explanation."""
    from app.agents.eligibility_agent import evaluate_eligibility
    case = MockCase(custody_days=140, max_sentence_days=360, repeat_offender=False)
    res = evaluate_eligibility(case)
    assert "eligible" in res
    assert "is_eligible" in res
    assert "rule_version" in res
    assert "threshold_fraction" in res
    assert "statutory_threshold_fraction" in res
    assert "threshold_days" in res
    assert "countable_custody_days" in res
    assert "explanation" in res
    assert res["eligible"] is True


# ── Test 23: Fail-Closed Invalid Rule ID (No Silent Fallback) ─────────────────
def test_invalid_rule_id_returns_404_no_silent_fallback():
    """An invalid rule ID must return 404 / raise KeyError, never silently fall back to V1."""
    # 1. Registry level
    with pytest.raises(KeyError) as exc_info:
        rule_service.registry.get_rule("RULE-BNSS-479-THRESHOLD-V99")
    assert "not found" in str(exc_info.value).lower()

    # 2. Service level get_rule
    assert rule_service.get_rule("RULE-BNSS-479-THRESHOLD-V99") is None

    # 3. API level evaluate endpoint
    headers = _token(Role.DEFENSE_ADVOCATE)
    payload = {
        "case_id": "ADHOC-FAIL",
        "custody_days": 135,
        "max_sentence_days": 365,
    }
    resp = client.post("/rules/RULE-BNSS-479-THRESHOLD-V99/evaluate", json=payload, headers=headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── Test 24: Persistent DB Reconstruction Across Cache Clear (Simulated Restart)
def test_persistent_db_reconstruction_across_server_restart():
    """Verify historical assessment reconstruction loads from database after cache is cleared."""
    from app.rules.service import _RULE_EXECUTIONS
    case = MockCase(case_id="UTP-PERSIST-TEST", custody_days=130, max_sentence_days=360)
    res = rule_service.evaluate_case(case)
    exec_id = res.execution_id

    # Verify present in memory
    assert exec_id in _RULE_EXECUTIONS

    # Simulate server restart by wiping in-memory execution cache
    _RULE_EXECUTIONS.clear()
    assert exec_id not in _RULE_EXECUTIONS

    # Now call reconstruct_assessment - must query persistent database table
    reconstructed = rule_service.reconstruct_assessment(exec_id)
    assert reconstructed is not None
    assert reconstructed["execution_id"] == exec_id
    assert reconstructed["case_id"] == "UTP-PERSIST-TEST"
    assert reconstructed["machine_status"] == RuleMachineStatus.THRESHOLD_REACHED.value
    assert reconstructed["input_snapshot"]["custody_days"] == 130


# ── Test 25: Truthful Baseline Labeling (No Fabricated Approvals) ─────────────
def test_demo_baseline_truthful_labeling_no_fabricated_approvals():
    """Verify canonical baseline rule is labeled as DEMO_BASELINE without fake approvals."""
    rule = rule_service.get_rule("RULE-BNSS-479-THRESHOLD-V1")
    assert rule is not None
    # Verify truthful demo labeling
    review_status = rule["legal_review_metadata"].get("status", "")
    assert "DEMO_BASELINE" in review_status
    assert "LEGAL VALIDATION REQUIRED" in review_status
    # Verify no fabricated individual approval
    assert rule["approval_metadata"].get("approved_by") is None


# ── Test 26: Unified Registry Compatibility Endpoint ──────────────────────────
def test_unified_registry_endpoint_no_duplicate_registries():
    """GET /rules/registry must project from the unified Stage 8 legal rules registry."""
    headers = _token(Role.SUPERVISING_LEGAL_OFFICER, user_id="demo_supervisor")
    res = client.get("/rules/registry", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "active_version" in data
    assert "rules" in data
    assert len(data["rules"]) >= 2
    rule_versions = [r["version_id"] for r in data["rules"]]
    assert "BNSS_479_RULESET_V1_2023" in rule_versions

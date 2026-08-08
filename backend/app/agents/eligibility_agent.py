"""
eligibility_agent.py — Deterministic Section 479 BNSS eligibility evaluator.

╔══════════════════════════════════════════════════════════════════════════╗
║  CRITICAL DESIGN RULE (from Nyaya_Mitra_Master_Roadmap_v2.md §2)        ║
║  The eligibility decision is NEVER made by an LLM.                      ║
║  This module is pure deterministic Python arithmetic — no AI calls.     ║
║  The LLM's role elsewhere is limited to explaining, retrieving,         ║
║  and drafting; it never decides custody status.                         ║
╚══════════════════════════════════════════════════════════════════════════╝

Section 479 BNSS thresholds
────────────────────────────
  First-time offender  →  must have served at least 1/3 of max sentence
  Repeat offender      →  must have served at least 1/2 of max sentence
"""

from __future__ import annotations
import math

from app.models.schemas import CaseRecord


# ── Constants ───────────────────────────────────────────────────────────────

_FIRST_TIME_FRACTION: float = 1 / 3   # Section 479 BNSS — first-time offenders
_REPEAT_FRACTION: float = 1 / 2       # Section 479 BNSS — repeat offenders

_LEGAL_BASIS_FIRST_TIME = (
    "Section 479 BNSS - First-Time Offender (1/3 Max Sentence Served)"
)
_LEGAL_BASIS_REPEAT = (
    "Section 479 BNSS - Standard Undertrial Threshold (1/2 Max Sentence Served)"
)


# ── Main evaluator ───────────────────────────────────────────────────────────

def evaluate_eligibility(case: CaseRecord) -> dict:
    """
    Evaluate whether an undertrial prisoner is eligible for bail under
    Section 479 BNSS based purely on deterministic arithmetic rules.

    Args:
        case: A validated CaseRecord instance (synthetic data only).

    Returns:
        A dict containing:
            case_id              — echoed from the input record
            eligible             — True if the prisoner has served the
                                   required fraction of the max sentence
            threshold_fraction   — 1/3 for first-time, 1/2 for repeat
            required_custody_days— minimum days that must be served
            custody_days_served  — actual days served (from the record)
            days_overdue         — how many days past threshold (0 if not yet)
            legal_basis          — human-readable citation string

    Example:
        >>> result = evaluate_eligibility(case)
        >>> result["eligible"]
        True
        >>> result["days_overdue"]
        167
    """
    # ── 1. Determine threshold fraction ─────────────────────────────────────
    is_repeat = case.urgency_flags.repeat_offender

    if not is_repeat:
        threshold_fraction = _FIRST_TIME_FRACTION
        legal_basis = _LEGAL_BASIS_FIRST_TIME
    else:
        threshold_fraction = _REPEAT_FRACTION
        legal_basis = _LEGAL_BASIS_REPEAT

    # ── 2. Calculate minimum required custody days ───────────────────────────
    # We use math.ceil() to ensure we never silently round down a legal threshold.
    # Note: The exact interpretation of statutory fractional days should be
    # validated with a legal expert before production deployment.
    required_days = math.ceil(case.max_sentence_days_for_offense * threshold_fraction)

    # ── 3. Evaluate eligibility ──────────────────────────────────────────────
    is_eligible = case.custody_days >= required_days
    days_overdue = max(0, case.custody_days - required_days)

    # ── 4. Build and return result dict ─────────────────────────────────────
    return {
        "case_id": case.case_id,
        "eligible": is_eligible,
        "threshold_fraction": threshold_fraction,
        "required_custody_days": required_days,
        "custody_days_served": case.custody_days,
        "days_overdue": days_overdue,
        "legal_basis": legal_basis,
    }


# ── Standalone smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from app.models.schemas import UrgencyFlags

    # ── Test Case A: Eligible first-time offender ────────────────────────────
    # Offense max: 730 days | Threshold (1/3): ceil(243.33) = 244 days | Served: 410 days
    # Expected: eligible=True, days_overdue=166
    case_a = CaseRecord(
        case_id="UTP-0007",
        name="synthetic - not a real person",
        offense_sections=["IPC 379"],
        arrest_date="2024-11-02",
        custody_days=410,
        max_sentence_days_for_offense=730,
        prior_bail_orders=[],
        required_docs=["remand_order", "charge_sheet"],
        present_docs=["remand_order", "charge_sheet"],
        urgency_flags=UrgencyFlags(age=63, health_flag=True, repeat_offender=False),
        jail_location="District Jail, synthetic",
        preferred_language="hi",
    )

    # ── Test Case B: Ineligible repeat offender ──────────────────────────────
    # Offense max: 1825 days | Threshold (1/2): 912 days | Served: 400 days
    # Expected: eligible=False, days_overdue=0
    case_b = CaseRecord(
        case_id="UTP-0012",
        name="synthetic - not a real person",
        offense_sections=["IPC 302"],
        arrest_date="2023-06-15",
        custody_days=400,
        max_sentence_days_for_offense=1825,
        prior_bail_orders=["BAIL-2021-004"],
        required_docs=["remand_order", "charge_sheet", "prior_bail_order_if_any"],
        present_docs=["remand_order"],
        urgency_flags=UrgencyFlags(age=34, health_flag=False, repeat_offender=True),
        jail_location="Central Jail, synthetic",
        preferred_language="ta",
    )

    print("=" * 60)
    print("ELIGIBILITY AGENT — SMOKE TEST")
    print("=" * 60)

    for label, case in [("Case A (First-Time Offender)", case_a), ("Case B (Repeat Offender)", case_b)]:
        result = evaluate_eligibility(case)
        print(f"\n{label}")
        print("-" * 40)
        print(json.dumps(result, indent=2))

        # Assertions
        if case.case_id == "UTP-0007":
            assert result["eligible"] is True,  "UTP-0007 should be eligible"
            assert result["days_overdue"] == 166, f"Expected 166, got {result['days_overdue']}"
            assert result["threshold_fraction"] == 1 / 3
            print("  [PASS] All assertions passed")

        if case.case_id == "UTP-0012":
            assert result["eligible"] is False, "UTP-0012 should NOT be eligible"
            assert result["days_overdue"] == 0,  "days_overdue must be 0 when not eligible"
            assert result["threshold_fraction"] == 1 / 2
            print("  [PASS] All assertions passed")

    print("\n" + "=" * 60)
    print("All smoke tests passed.")
    print("=" * 60)

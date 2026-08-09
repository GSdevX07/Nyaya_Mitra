"""
prioritization_agent.py Urgency scoring and case queue sorter for Nyaya Mitra.

Design pattern (from Nyaya_Mitra_Master_Roadmap_v2.md §9, Agent 2.3):
  - Fully deterministic weighted scoring no LLM involved.
  - Score formula: days_overdue + health_flag(50) + age>60(30) + first_time(20)
  - Completely explainable to a judge: every point awarded has a named reason.
  - The output sorted queue feeds directly into the lawyer dashboard.
"""

from __future__ import annotations

from app.models.schemas import CaseRecord


# ── Scoring weights (named constants for explainability) ─────────────────────

WEIGHT_HEALTH_FLAG: int = 50       # Documented serious health condition
WEIGHT_ELDERLY: int = 30           # Age above 60 elevated vulnerability
WEIGHT_FIRST_TIME_OFFENDER: int = 20  # First-time offenders get statutory preference
AGE_ELDERLY_THRESHOLD: int = 60


# ── Scoring function ─────────────────────────────────────────────────────────

def calculate_urgency_score(case: CaseRecord, days_overdue: int) -> int:
    """
    Compute a deterministic urgency score for a single case.

    Scoring breakdown:
        days_overdue                         → 1 point per day legally overdue
        health_flag is True                  → +50 points
        age > 60                             → +30 points
        repeat_offender is False (1st-time)  → +20 points

    All weights are named module-level constants so they can be tuned
    in one place without touching logic.

    Args:
        case:        A validated CaseRecord instance.
        days_overdue: Days the prisoner has been held past the eligibility
                      threshold (0 if not yet eligible never negative).

    Returns:
        Integer urgency score (higher = needs attention sooner).

    Example:
        >>> score = calculate_urgency_score(case, days_overdue=167)
        >>> score   # 167 overdue + 50 health + 30 elderly + 20 first-time
        267
    """
    score: int = days_overdue  # Base: one point per overdue day

    if case.urgency_flags.health_flag:
        score += WEIGHT_HEALTH_FLAG

    if case.urgency_flags.age > AGE_ELDERLY_THRESHOLD:
        score += WEIGHT_ELDERLY

    if not case.urgency_flags.repeat_offender:
        score += WEIGHT_FIRST_TIME_OFFENDER

    return score


# ── Queue sorter ─────────────────────────────────────────────────────────────

def prioritize_cases(case_evaluations: list[dict]) -> list[dict]:
    """
    Score and sort a list of case-evaluation dicts in descending urgency order.

    Each input dict must contain at minimum:
        "case"        → CaseRecord instance
        "days_overdue"→ int (0 if case is not yet eligible)

    The function mutates each dict in-place by appending "urgency_score",
    then returns the list sorted highest-score-first.

    Args:
        case_evaluations: List of dicts, one per case, produced by the
                          orchestrator after the Eligibility Agent has run.

    Returns:
        The same list, sorted descending by "urgency_score", with the score
        appended to every dict.

    Example:
        >>> queue = prioritize_cases([
        ...     {"case": case_a, "days_overdue": 167},
        ...     {"case": case_b, "days_overdue": 0},
        ... ])
        >>> queue[0]["case"].case_id   # highest urgency first
        'UTP-0007'
    """
    for entry in case_evaluations:
        entry["urgency_score"] = calculate_urgency_score(
            case=entry["case"],
            days_overdue=entry["days_overdue"],
        )

    return sorted(case_evaluations, key=lambda e: e["urgency_score"], reverse=True)


# ── Standalone smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    from app.models.schemas import UrgencyFlags

    # ── Case 1: Standard case moderate overdue, no special flags ───────────
    # Expected score: 40 overdue + 20 first-time = 60
    case_standard = CaseRecord(
        case_id="UTP-0001",
        name="synthetic - not a real person",
        offense_sections=["IPC 323"],
        arrest_date="2025-01-10",
        custody_days=200,
        max_sentence_days_for_offense=365,
        prior_bail_orders=[],
        required_docs=["remand_order", "charge_sheet"],
        present_docs=["remand_order", "charge_sheet"],
        urgency_flags=UrgencyFlags(age=28, health_flag=False, repeat_offender=False),
        jail_location="Sub-Jail, synthetic",
        preferred_language="en",
    )

    # ── Case 2: Senior citizen with health issues low overdue, high flags ──
    # Expected score: 10 overdue + 50 health + 30 elderly + 20 first-time = 110
    case_senior_health = CaseRecord(
        case_id="UTP-0007",
        name="synthetic - not a real person",
        offense_sections=["IPC 379"],
        arrest_date="2024-11-02",
        custody_days=260,
        max_sentence_days_for_offense=730,
        prior_bail_orders=[],
        required_docs=["remand_order", "charge_sheet"],
        present_docs=["remand_order", "charge_sheet"],
        urgency_flags=UrgencyFlags(age=63, health_flag=True, repeat_offender=False),
        jail_location="District Jail, synthetic",
        preferred_language="hi",
    )

    # ── Case 3: Highly overdue repeat offender, no health/age flags ──────────
    # Expected score: 300 overdue + 0 (repeat offender, no age, no health) = 300
    case_highly_overdue = CaseRecord(
        case_id="UTP-0015",
        name="synthetic - not a real person",
        offense_sections=["IPC 392"],
        arrest_date="2023-03-01",
        custody_days=850,
        max_sentence_days_for_offense=1095,
        prior_bail_orders=["BAIL-2022-007"],
        required_docs=["remand_order", "charge_sheet", "prior_bail_order_if_any"],
        present_docs=["remand_order", "charge_sheet", "prior_bail_order_if_any"],
        urgency_flags=UrgencyFlags(age=40, health_flag=False, repeat_offender=True),
        jail_location="Central Jail, synthetic",
        preferred_language="ta",
    )

    # days_overdue for each case (would normally come from the Eligibility Agent)
    case_evaluations = [
        {"case": case_standard,      "days_overdue": 40},
        {"case": case_senior_health,  "days_overdue": 10},
        {"case": case_highly_overdue, "days_overdue": 300},
    ]

    sorted_queue = prioritize_cases(case_evaluations)

    print("=" * 60)
    print("PRIORITIZATION AGENT -- SMOKE TEST")
    print("=" * 60)
    print(f"\n{'Rank':<6}{'Case ID':<12}{'Days Overdue':<16}{'Score':<10}{'Breakdown'}")
    print("-" * 70)

    for rank, entry in enumerate(sorted_queue, start=1):
        c = entry["case"]
        flags = c.urgency_flags
        breakdown_parts = [f"{entry['days_overdue']} overdue"]
        if flags.health_flag:
            breakdown_parts.append(f"+{WEIGHT_HEALTH_FLAG} health")
        if flags.age > AGE_ELDERLY_THRESHOLD:
            breakdown_parts.append(f"+{WEIGHT_ELDERLY} elderly")
        if not flags.repeat_offender:
            breakdown_parts.append(f"+{WEIGHT_FIRST_TIME_OFFENDER} first-time")
        breakdown = " | ".join(breakdown_parts)

        print(f"{rank:<6}{c.case_id:<12}{entry['days_overdue']:<16}{entry['urgency_score']:<10}{breakdown}")

    print()

    # Assertions
    ids_in_order = [e["case"].case_id for e in sorted_queue]

    assert sorted_queue[0]["case"].case_id == "UTP-0015", "Highly overdue case should be #1"
    assert sorted_queue[1]["case"].case_id == "UTP-0007", "Senior with health issues should be #2"
    assert sorted_queue[2]["case"].case_id == "UTP-0001", "Standard case should be #3"

    assert sorted_queue[0]["urgency_score"] == 300, f"Expected 300, got {sorted_queue[0]['urgency_score']}"
    assert sorted_queue[1]["urgency_score"] == 110, f"Expected 110, got {sorted_queue[1]['urgency_score']}"
    assert sorted_queue[2]["urgency_score"] == 60,  f"Expected 60, got {sorted_queue[2]['urgency_score']}"

    print("[PASS] Sorted order:  UTP-0015 > UTP-0007 > UTP-0001")
    print("[PASS] Scores:        300 > 110 > 60")
    print("[PASS] All assertions passed")
    print("\n" + "=" * 60)
    print("All smoke tests passed.")
    print("=" * 60)

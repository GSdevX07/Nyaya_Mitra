"""
completeness_agent.py — Records Completeness Agent for Nyaya Mitra.

Design pattern (from Nyaya_Mitra_Master_Roadmap_v2.md §9, Agent 2.2):
  - Deterministic core: the missing-documents diff is pure set arithmetic.
    No LLM is used to decide whether documents are missing.
  - LLM is used ONLY to phrase the human-readable alert sentence that a
    records officer will read — a formatting task, not a decision.
  - If the LLM is unavailable, the agent still returns full structured data;
    only the message string degrades to a plain-text fallback.
"""

from __future__ import annotations

from app.llm_client import generate
from app.models.schemas import CaseRecord


# ── Main evaluator ───────────────────────────────────────────────────────────

def evaluate_completeness(case: CaseRecord) -> dict:
    """
    Check whether all required documents for a case are present, and
    generate a records-office alert for any that are missing.

    The missing-docs determination is fully deterministic (set difference).
    The LLM is invoked only to produce the human-readable alert sentence,
    and only when at least one document is missing.

    Args:
        case: A validated CaseRecord instance (synthetic data only).

    Returns:
        A dict containing:
            case_id     — echoed from the input record
            is_complete — True if no documents are missing
            missing_docs— list of document names that are absent
            message     — "All required documents are present." when complete,
                          or an LLM-drafted alert sentence when incomplete

    Example (complete):
        >>> result = evaluate_completeness(case_with_all_docs)
        >>> result["is_complete"]
        True

    Example (incomplete):
        >>> result = evaluate_completeness(case_missing_charge_sheet)
        >>> result["is_complete"]
        False
        >>> "charge_sheet" in result["missing_docs"]
        True
    """
    # ── 1. Deterministic diff — no LLM involved ──────────────────────────────
    required = set(case.required_docs)
    present = set(case.present_docs)
    missing_docs: list[str] = sorted(required - present)   # sorted for stable output

    # ── 2. Early return if nothing is missing ────────────────────────────────
    if not missing_docs:
        return {
            "case_id": case.case_id,
            "is_complete": True,
            "missing_docs": [],
            "message": "All required documents are present.",
        }

    # ── 3. LLM phrases the alert (only reaches here when docs ARE missing) ───
    missing_docs_list = ", ".join(missing_docs)

    prompt = (
        f"Draft a polite, one-sentence automated alert to the prison records office "
        f"requesting the following missing documents for case {case.case_id}: "
        f"{missing_docs_list}. "
        f"Do not include pleasantries or email signatures, just the requested sentence."
    )
    system = "You are an automated legal-aid system assistant."

    try:
        message = generate(prompt=prompt, system=system)
    except RuntimeError as exc:
        # All LLM providers failed — degrade gracefully with a plain-text alert
        # so the structured data (missing_docs) is still usable downstream.
        message = (
            f"ALERT: The following documents are missing for case "
            f"{case.case_id} and must be submitted to proceed with the "
            f"bail application: {missing_docs_list}."
        )
        import logging
        logging.getLogger(__name__).error(
            "completeness_agent: LLM unavailable, using fallback message. Error: %s", exc
        )

    # ── 4. Return full result dict ───────────────────────────────────────────
    return {
        "case_id": case.case_id,
        "is_complete": False,
        "missing_docs": missing_docs,
        "message": message,
    }


# ── Standalone smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from app.models.schemas import UrgencyFlags

    # ── Test Case A: Missing "charge_sheet" ──────────────────────────────────
    case_incomplete = CaseRecord(
        case_id="UTP-0007",
        name="synthetic - not a real person",
        offense_sections=["IPC 379"],
        arrest_date="2024-11-02",
        custody_days=410,
        max_sentence_days_for_offense=730,
        prior_bail_orders=[],
        required_docs=["remand_order", "charge_sheet", "prior_bail_order_if_any"],
        present_docs=["remand_order"],          # charge_sheet and prior_bail_order_if_any missing
        urgency_flags=UrgencyFlags(age=63, health_flag=True, repeat_offender=False),
        jail_location="District Jail, synthetic",
        preferred_language="hi",
    )

    # ── Test Case B: All documents present ───────────────────────────────────
    case_complete = CaseRecord(
        case_id="UTP-0003",
        name="synthetic - not a real person",
        offense_sections=["IPC 323"],
        arrest_date="2025-01-10",
        custody_days=200,
        max_sentence_days_for_offense=365,
        prior_bail_orders=[],
        required_docs=["remand_order", "charge_sheet"],
        present_docs=["remand_order", "charge_sheet"],   # all docs present
        urgency_flags=UrgencyFlags(age=28, health_flag=False, repeat_offender=False),
        jail_location="Sub-Jail, synthetic",
        preferred_language="en",
    )

    print("=" * 60)
    print("COMPLETENESS AGENT -- SMOKE TEST")
    print("=" * 60)

    for label, case in [
        ("Case A (Incomplete - missing charge_sheet + prior_bail_order_if_any)", case_incomplete),
        ("Case B (Complete - all docs present)", case_complete),
    ]:
        result = evaluate_completeness(case)
        print(f"\n{label}")
        print("-" * 40)
        print(json.dumps(result, indent=2))

        # Assertions
        if case.case_id == "UTP-0007":
            assert result["is_complete"] is False, "UTP-0007 should be incomplete"
            assert "charge_sheet" in result["missing_docs"], "charge_sheet must be flagged"
            assert "prior_bail_order_if_any" in result["missing_docs"], "prior_bail_order_if_any must be flagged"
            assert result["message"] != "", "message must not be empty"
            print("  [PASS] All assertions passed")

        if case.case_id == "UTP-0003":
            assert result["is_complete"] is True, "UTP-0003 should be complete"
            assert result["missing_docs"] == [], "missing_docs must be empty"
            assert result["message"] == "All required documents are present."
            print("  [PASS] All assertions passed")

    print("\n" + "=" * 60)
    print("All smoke tests passed.")
    print("=" * 60)

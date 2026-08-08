"""
explainer_agent.py — Multilingual Explainer Agent for Nyaya Mitra.

Design pattern (from Nyaya_Mitra_Master_Roadmap_v2.md §9, Agent 2.7):
  - Humanizes the pitch: this is the family-facing side of the system.
  - The explanation is generated in the prisoner's preferred language,
    making legal status accessible to families with no legal background.
  - The system prompt explicitly bans jargon and limits output to 150 words,
    making it suitable for reading aloud over a phone call.
  - This agent is always safe to call regardless of eligibility status —
    it explains the current situation honestly, whether eligible or not.
"""

from __future__ import annotations

from app.llm_client import generate
from app.models.schemas import CaseRecord


# ── System prompt ────────────────────────────────────────────────────────────
# Kept as a named constant for easy tuning without touching agent logic.

EXPLAINER_SYSTEM_PROMPT: str = (
    "You are a helpful assistant for a legal-aid clinic. "
    "Explain the legal status in simple, non-legal language suitable for "
    "reading aloud to a family member. No jargon. Keep it under 150 words."
)


# ── Explainer function ───────────────────────────────────────────────────────

def generate_explanation(case: CaseRecord, eligibility_details: dict) -> dict:
    """
    Generate a plain-language explanation of a prisoner's bail eligibility
    status in their preferred language.

    The LLM is instructed to avoid legal jargon and stay under 150 words —
    the output is meant to be read aloud to a family member by a legal-aid
    volunteer, not submitted as a formal document.

    Args:
        case:                A validated CaseRecord instance.
        eligibility_details: Dict produced by the Eligibility Agent, containing
                             at minimum:
                               "eligible"    → bool
                               "days_overdue"→ int

    Returns:
        A dict containing:
            case_id    — echoed from the input record
            explanation— LLM-generated plain-language explanation string
            language   — value of case.preferred_language (for the UI to label
                         which language the explanation was generated in)

    Example:
        >>> result = generate_explanation(case, {"eligible": True, "days_overdue": 167})
        >>> result["language"]
        'hi'
        >>> isinstance(result["explanation"], str)
        True
    """
    # ── Construct user prompt (template from Roadmap §14) ────────────────────
    user_prompt = (
        f"Target Language: {case.preferred_language}\n\n"
        f"Facts: "
        f"Eligibility Result: {eligibility_details['eligible']}, "
        f"Days Overdue: {eligibility_details['days_overdue']}, "
        f"Next Step: Pending Lawyer Review.\n\n"
        f"Task: Generate the explanation."
    )

    # ── Call LLM via the single choke-point ─────────────────────────────────
    explanation = generate(prompt=user_prompt, system=EXPLAINER_SYSTEM_PROMPT)

    return {
        "case_id": case.case_id,
        "explanation": explanation,
        "language": case.preferred_language,
    }


# ── Standalone smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    from app.models.schemas import UrgencyFlags

    # ── Test Case A: Eligible prisoner — Hindi explanation ───────────────────
    case_hindi = CaseRecord(
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

    eligibility_eligible = {
        "eligible": True,
        "days_overdue": 167,
    }

    # ── Test Case B: Ineligible prisoner — Tamil explanation ─────────────────
    case_tamil = CaseRecord(
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

    eligibility_ineligible = {
        "eligible": False,
        "days_overdue": 0,
    }

    print("=" * 60)
    print("EXPLAINER AGENT -- SMOKE TEST")
    print("=" * 60)

    test_cases = [
        ("Case A (Eligible | Language: Hindi / hi)", case_hindi, eligibility_eligible),
        ("Case B (Ineligible | Language: Tamil / ta)", case_tamil, eligibility_ineligible),
    ]

    for label, case, eligibility in test_cases:
        print(f"\n{label}")
        print("-" * 40)
        result = generate_explanation(case, eligibility_details=eligibility)

        print(f"case_id    : {result['case_id']}")
        print(f"language   : {result['language']}")
        print(f"explanation: {result['explanation']}")

        # Assertions
        assert result["case_id"] == case.case_id, "case_id must be echoed"
        assert result["language"] == case.preferred_language, "language must match case preference"
        assert isinstance(result["explanation"], str), "explanation must be a string"
        assert len(result["explanation"]) > 0, "explanation must be non-empty"
        print("  [PASS] case_id, language, and explanation all valid")

    print("\n" + "=" * 60)
    print("All smoke tests passed.")
    print("=" * 60)

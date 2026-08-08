"""
drafting_agent.py — LLM-powered bail application drafter for Nyaya Mitra.

Design pattern (from Nyaya_Mitra_Master_Roadmap_v2.md §9, Agent 2.6):
  - This is the primary "wow" demo moment — a real generated legal document.
  - The system prompt explicitly restricts the LLM to ONLY the retrieved
    statute/precedent text — no hallucinated law is introduced.
  - This agent should only be called when retrieved_law is non-empty
    (i.e., after the Retrieval Agent confirms eligibility and returns text).
  - The output is always routed through a human-lawyer approval gate before
    anything is "filed" — the UI enforces this; this agent only produces a draft.
"""

from __future__ import annotations

from app.llm_client import generate
from app.models.schemas import CaseRecord


# ── System prompt (from Nyaya_Mitra_Master_Roadmap_v2.md §14) ───────────────
# Kept as a named constant so it can be tuned in one place without touching
# agent logic. Mirror any changes here in prompts.py if that file is added.

DRAFTING_SYSTEM_PROMPT: str = (
    "You are drafting a bail application for a legal-aid lawyer's review. "
    "Use ONLY the retrieved statute/precedent text provided — do not add legal "
    "claims not present in it. Flag clearly if a required fact is missing "
    "rather than inferring it."
)


# ── Drafting function ────────────────────────────────────────────────────────

def draft_bail_application(case: CaseRecord, retrieved_law: str) -> dict:
    """
    Generate a formal bail application draft grounded in retrieved statute text.

    The LLM is instructed via the system prompt to cite only the provided
    statute/precedent and to flag gaps rather than infer missing facts —
    this is the core hallucination-prevention measure for this agent.

    Args:
        case:          A validated CaseRecord for an eligible prisoner.
        retrieved_law: Statute/precedent text returned by the Retrieval Agent.
                       Should be non-empty; passing an empty string will result
                       in the LLM flagging missing facts (intended behaviour).

    Returns:
        A dict containing:
            case_id          — echoed from the input record
            drafted_document — LLM-generated bail application text (or the
                               dev-mode placeholder if providers are not
                               yet configured)

    Example:
        >>> result = draft_bail_application(case, retrieved_law=statute_text)
        >>> isinstance(result["drafted_document"], str)
        True
        >>> result["case_id"]
        'UTP-0007'
    """
    # ── Construct user prompt ────────────────────────────────────────────────
    user_prompt = (
        f"Case Facts: {case.model_dump()}\n\n"
        f"Retrieved Law: {retrieved_law}\n\n"
        f"Task: Draft a formal bail application citing the specific retrieved section."
    )

    # ── Call LLM via the single choke-point ─────────────────────────────────
    drafted_document = generate(prompt=user_prompt, system=DRAFTING_SYSTEM_PROMPT)

    return {
        "case_id": case.case_id,
        "drafted_document": drafted_document,
    }


# ── Standalone smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    from app.models.schemas import UrgencyFlags

    mock_case = CaseRecord(
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

    mock_retrieved_law = (
        "Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023: "
        "Where a person has, during the period of investigation, inquiry or trial "
        "under this Sanhita of an offence under any law (not being an offence for "
        "which the punishment of death or life imprisonment has been specified as "
        "one of the punishments under that law) undergone detention for a period "
        "extending up to one-half of the maximum period of imprisonment specified "
        "for that offence under that law, he shall be released by the Court on bail: "
        "Provided that where such person is a first-time offender... he shall be "
        "released on bond by the Court, if he has undergone detention for the period "
        "extending up to one-third of the maximum period of imprisonment.\n\n"
        "Supreme Court ruling: Prolonged incarceration during pendency of trial "
        "violates Article 21 of the Constitution."
    )

    print("=" * 60)
    print("DRAFTING AGENT -- SMOKE TEST")
    print("=" * 60)
    print(f"\nCase ID   : {mock_case.case_id}")
    print(f"Offense   : {mock_case.offense_sections}")
    print(f"Days Held : {mock_case.custody_days}")
    print("-" * 60)
    print("Calling generate() via llm_client...\n")

    result = draft_bail_application(mock_case, retrieved_law=mock_retrieved_law)

    print("--- DRAFTED DOCUMENT ---")
    print(result["drafted_document"])
    print("------------------------")

    # Assertions
    assert result["case_id"] == "UTP-0007", "case_id must be echoed"
    assert isinstance(result["drafted_document"], str), "drafted_document must be a string"
    assert len(result["drafted_document"]) > 0, "drafted_document must be non-empty"

    print("\n[PASS] case_id echoed correctly")
    print("[PASS] drafted_document is a non-empty string")
    print("\n" + "=" * 60)
    print("Smoke test passed.")
    print("=" * 60)

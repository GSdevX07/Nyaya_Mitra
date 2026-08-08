"""
retrieval_agent.py — RAG Retrieval Agent for Nyaya Mitra.

Design pattern (from Nyaya_Mitra_Master_Roadmap_v2.md §9, Agent 2.5):
  - Determines WHICH legal text to retrieve based on case eligibility.
  - The actual retrieval is delegated to the vector_store layer, which is
    swappable between the mock dict and a real ChromaDB index.
  - If a case is not yet eligible, no statute text is retrieved — this avoids
    generating a draft bail application for ineligible cases downstream.
"""

from __future__ import annotations

from app.models.schemas import CaseRecord
from app.rag.vector_store import retrieve_legal_text


# ── Query key mapping ────────────────────────────────────────────────────────
# Centralise which statute keys are relevant for eligible cases.
# Extend this list as more statutes / precedents are indexed.

ELIGIBLE_QUERY_KEYS: list[str] = ["BNSS_479", "PRECEDENT_DELAY"]


# ── Retrieval function ───────────────────────────────────────────────────────

def execute_retrieval(case: CaseRecord, is_eligible: bool) -> dict:
    """
    Retrieve relevant statute and precedent text for a case if it is eligible.

    For eligible cases, fetches BNSS Section 479 text and the Article 21
    Supreme Court precedent on prolonged incarceration — the two grounding
    chunks the Drafting Agent needs to produce a legally sound bail application.

    For ineligible cases, returns an empty string so the orchestrator can
    skip the Drafting Agent without raising an error.

    Args:
        case:        A validated CaseRecord instance (synthetic data only).
        is_eligible: Boolean result from the Eligibility Agent's evaluation.

    Returns:
        A dict containing:
            case_id            — echoed from the input record
            retrieved_statutes — concatenated statute/precedent text if eligible,
                                 empty string if not eligible

    Example (eligible):
        >>> result = execute_retrieval(case, is_eligible=True)
        >>> "Section 479" in result["retrieved_statutes"]
        True

    Example (ineligible):
        >>> result = execute_retrieval(case, is_eligible=False)
        >>> result["retrieved_statutes"]
        ''
    """
    if not is_eligible:
        return {
            "case_id": case.case_id,
            "retrieved_statutes": "",
        }

    retrieved_text = retrieve_legal_text(query_keys=ELIGIBLE_QUERY_KEYS)

    return {
        "case_id": case.case_id,
        "retrieved_statutes": retrieved_text,
    }


# ── Standalone smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from app.models.schemas import UrgencyFlags

    # ── Shared mock case ─────────────────────────────────────────────────────
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

    print("=" * 60)
    print("RETRIEVAL AGENT -- SMOKE TEST")
    print("=" * 60)

    # ── Test 1: Eligible case — should return statute text ───────────────────
    print("\nTest 1: is_eligible=True")
    print("-" * 40)
    result_eligible = execute_retrieval(mock_case, is_eligible=True)
    print(f"case_id          : {result_eligible['case_id']}")
    print(f"retrieved_statutes:\n{result_eligible['retrieved_statutes']}")

    assert result_eligible["case_id"] == "UTP-0007"
    assert "Section 479" in result_eligible["retrieved_statutes"], \
        "BNSS_479 text must be present for eligible case"
    assert "Article 21" in result_eligible["retrieved_statutes"], \
        "PRECEDENT_DELAY text must be present for eligible case"
    assert result_eligible["retrieved_statutes"] != ""
    print("\n  [PASS] Retrieved text contains Section 479 and Article 21 precedent")

    # ── Test 2: Ineligible case — should return empty string ─────────────────
    print("\nTest 2: is_eligible=False")
    print("-" * 40)
    result_ineligible = execute_retrieval(mock_case, is_eligible=False)
    print(f"case_id          : {result_ineligible['case_id']}")
    print(f"retrieved_statutes: '{result_ineligible['retrieved_statutes']}'")

    assert result_ineligible["retrieved_statutes"] == "", \
        "retrieved_statutes must be empty string for ineligible case"
    print("  [PASS] retrieved_statutes is empty for ineligible case")

    print("\n" + "=" * 60)
    print("All smoke tests passed.")
    print("=" * 60)

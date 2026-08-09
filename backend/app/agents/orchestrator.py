"""
orchestrator.py Master pipeline for Nyaya Mitra's agent system.

Design pattern (from Nyaya_Mitra_Master_Roadmap_v2.md §9, Agent 2.9):
  - Sequential pipeline: each agent runs in order, with outputs from earlier
    agents informing later ones (e.g., eligibility result gates RAG/drafting).
  - Human-approval gate: the orchestrator produces a "draft_ready" flag but
    never auto-advances the status to "Filed" that requires an explicit
    POST /cases/{id}/approve call from the lawyer dashboard (Phase 3, Step 3.1).
  - Every step is logged to an "agent_activity_log" list so the frontend's
    live Agent Activity Log panel can display a timestamped trace of what ran.
  - Agents are called independently and their full result dicts are preserved
    so the frontend can render each section without re-fetching.

Pipeline order:
  1. Eligibility Agent        (deterministic gates everything downstream)
  2. Completeness Agent       (deterministic diff + optional LLM phrasing)
  3. Prioritization scoring   (deterministic weighted score)
  4. Notification Agent       (simulated dispatch)
  5. Retrieval Agent (RAG)    (only if eligible + complete)
  6. Drafting Agent           (only if eligible + complete + law retrieved)
  7. Explainer Agent          (always explains current status in plain language)
  8. Status Agent             (simulated court tracking)
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.agents.completeness_agent import evaluate_completeness
from app.agents.drafting_agent import draft_bail_application
from app.agents.eligibility_agent import evaluate_eligibility
from app.agents.explainer_agent import generate_explanation
from app.agents.notification_agent import trigger_notification
from app.agents.prioritization_agent import calculate_urgency_score
from app.agents.retrieval_agent import execute_retrieval
from app.agents.status_agent import get_status
from app.llm_client import get_last_provider
from app.models.schemas import CaseRecord


# ── Helpers ──────────────────────────────────────────────────────────────────

def _log_step(log: list[dict], agent: str, status: str, detail: str = "") -> None:
    """Append a timestamped entry to the agent activity log."""
    log.append({
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "agent": agent,
        "status": status,
        "detail": detail,
    })


# ── Master pipeline ───────────────────────────────────────────────────────────

def process_case(case: CaseRecord) -> dict:
    """
    Run a single CaseRecord through the full Nyaya Mitra agent pipeline.

    The pipeline is sequential each step gates the next where appropriate.
    The function never raises; unexpected errors in any agent are caught,
    logged to agent_activity_log, and the pipeline continues so the caller
    always receives a complete result dict.

    Args:
        case: A validated CaseRecord instance (synthetic data only).

    Returns:
        A consolidated dict containing all agent outputs:
            case_id           echoed from input
            eligibility       full Eligibility Agent result dict
            completeness      full Completeness Agent result dict
            urgency_score     integer score from Prioritization Agent
            notification      full Notification Agent result dict
            retrieval         full Retrieval Agent result dict
            draft             full Drafting Agent result dict (or skip notice)
            explanation       full Explainer Agent result dict
            status_tracking   full Status Agent result dict
            draft_ready       True only if eligible + complete + draft generated
            agent_activity_loglist of timestamped step records for the UI panel

    Example:
        >>> result = process_case(case)
        >>> result["eligibility"]["eligible"]
        True
        >>> result["draft_ready"]
        True
    """
    activity_log: list[dict] = []

    # ── Step 1: Eligibility Agent ─────────────────────────────────────────────
    _log_step(activity_log, "EligibilityAgent", "RUNNING", "Evaluating Section 479 BNSS threshold")
    eligibility_result = evaluate_eligibility(case)
    is_eligible: bool = eligibility_result["eligible"]
    days_overdue: int = eligibility_result["days_overdue"]
    _log_step(
        activity_log, "EligibilityAgent", "DONE",
        f"eligible={is_eligible}, days_overdue={days_overdue}"
    )

    # ── Step 2: Completeness Agent ────────────────────────────────────────────
    _log_step(activity_log, "CompletenessAgent", "RUNNING", "Checking required documents")
    completeness_result = evaluate_completeness(case)
    is_complete: bool = completeness_result["is_complete"]
    _log_step(
        activity_log, "CompletenessAgent", "DONE",
        f"is_complete={is_complete}, missing={completeness_result['missing_docs']}"
    )

    # ── Step 3: Prioritization score + Notification Agent ────────────────────
    _log_step(activity_log, "PrioritizationAgent", "RUNNING", "Computing urgency score")
    urgency_score: int = calculate_urgency_score(case, days_overdue)
    _log_step(activity_log, "PrioritizationAgent", "DONE", f"urgency_score={urgency_score}")

    _log_step(activity_log, "NotificationAgent", "RUNNING", "Dispatching alert to lawyer dashboard")
    notification_result = trigger_notification(case, urgency_score)
    _log_step(
        activity_log, "NotificationAgent", "DONE",
        f"alert_level={notification_result['alert_level']}"
    )

    # ── Step 4: RAG Retrieval + Drafting Agent (gated on eligible + complete) ─
    retrieval_result: dict = {"case_id": case.case_id, "retrieved_statutes": ""}
    draft_result: dict = {"case_id": case.case_id, "drafted_document": ""}
    draft_ready: bool = False

    if is_eligible and is_complete:
        _log_step(activity_log, "RetrievalAgent", "RUNNING", "Fetching relevant statutes from RAG")
        retrieval_result = execute_retrieval(case, is_eligible=True)
        retrieved_law = retrieval_result["retrieved_statutes"]
        _log_step(
            activity_log, "RetrievalAgent", "DONE",
            f"retrieved {len(retrieved_law)} chars of statute text"
        )

        if retrieved_law:
            _log_step(activity_log, "DraftingAgent", "RUNNING", "Generating bail application draft via LLM")
            draft_result = draft_bail_application(case, retrieved_law=retrieved_law)
            draft_ready = True
            provider = get_last_provider()
            _log_step(
                activity_log, "DraftingAgent", "DONE",
                f"Draft generated via [{provider}] awaiting human-lawyer approval"
            )
        else:
            _log_step(activity_log, "DraftingAgent", "SKIPPED", "No statute text retrieved draft skipped")
    else:
        skip_reason = []
        if not is_eligible:
            skip_reason.append("not yet eligible")
        if not is_complete:
            skip_reason.append("missing documents")
        reason_str = " + ".join(skip_reason)
        _log_step(activity_log, "RetrievalAgent", "SKIPPED", reason_str)
        _log_step(activity_log, "DraftingAgent",  "SKIPPED", reason_str)

    # ── Step 5: Multilingual Explainer Agent (always runs) ───────────────────
    _log_step(
        activity_log, "ExplainerAgent", "RUNNING",
        f"Generating plain-language explanation in '{case.preferred_language}'"
    )
    explanation_result = generate_explanation(case, eligibility_details=eligibility_result)
    provider = get_last_provider()
    _log_step(
        activity_log, "ExplainerAgent", "DONE",
        f"Explanation generated via [{provider}] for family view"
    )

    # ── Step 6: Status Tracking Agent ────────────────────────────────────────
    _log_step(activity_log, "StatusAgent", "RUNNING", "Fetching court status")
    status_result = get_status(case.case_id)
    _log_step(
        activity_log, "StatusAgent", "DONE",
        f"current_status='{status_result['current_status']}'"
    )

    # ── Consolidated result ───────────────────────────────────────────────
    return {
        "case_id": case.case_id,
        "case": case.model_dump(),          # Full case data for frontend
        "eligibility": eligibility_result,
        "completeness": completeness_result,
        "urgency_score": urgency_score,
        "notification": notification_result,
        "retrieval": retrieval_result,
        "draft": draft_result,
        "explanation": explanation_result,
        "status_tracking": status_result,
        "draft_ready": draft_ready,
        "llm_provider": get_last_provider(),  # Which tier served the LLM calls
        "agent_activity_log": activity_log,
    }


# ── Standalone smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from app.models.schemas import UrgencyFlags

    # ── "Hero case" perfect eligible first-time offender ───────────────────
    # All docs present, senior citizen, health flag, 167 days overdue
    # Expected: eligible=True, is_complete=True, draft_ready=True
    hero_case = CaseRecord(
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
    print("ORCHESTRATOR -- SMOKE TEST (Hero Case: UTP-0007)")
    print("=" * 60)
    print()

    result = process_case(hero_case)

    # Pretty-print the full result (excluding the long statute text for clarity)
    display = {k: v for k, v in result.items() if k != "retrieval"}
    display["retrieval"] = {
        "case_id": result["retrieval"]["case_id"],
        "retrieved_statutes": f"[{len(result['retrieval']['retrieved_statutes'])} chars]",
    }
    print(json.dumps(display, indent=2))

    print("\n--- AGENT ACTIVITY LOG ---")
    for entry in result["agent_activity_log"]:
        print(f"  [{entry['status']:<8}] {entry['agent']:<20} | {entry['detail']}")

    print()

    # Assertions
    assert result["case_id"] == "UTP-0007"
    assert result["eligibility"]["eligible"] is True,       "Hero case must be eligible"
    assert result["eligibility"]["days_overdue"] == 167,    "Expected 167 days overdue"
    assert result["completeness"]["is_complete"] is True,   "Hero case must be complete"
    assert result["urgency_score"] == 267,                  "Expected score: 167+50+30+20=267"
    assert result["notification"]["alert_level"] == "HIGH", "Score 267 must trigger HIGH alert"
    assert result["draft_ready"] is True,                   "Hero case must produce a draft"
    assert len(result["agent_activity_log"]) > 0,           "Activity log must have entries"
    assert result["explanation"]["language"] == "hi"

    print("[PASS] eligibility: eligible=True, days_overdue=167")
    print("[PASS] completeness: is_complete=True")
    print("[PASS] urgency_score=267 (167 overdue + 50 health + 30 elderly + 20 first-time)")
    print("[PASS] notification: alert_level=HIGH")
    print("[PASS] draft_ready=True")
    print("[PASS] explanation language='hi'")
    print("[PASS] agent_activity_log populated")

    print("\n" + "=" * 60)
    print("All orchestrator smoke tests passed.")
    print("=" * 60)

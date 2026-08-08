"""
notification_agent.py — Simulated alert dispatcher for Nyaya Mitra.

Design pattern (from Nyaya_Mitra_Master_Roadmap_v2.md §9, Agent 2.4):
  - This agent is EXPLICITLY SIMULATED — no real SMS/email gateway is wired up.
  - In production this would integrate with an SMS gateway (e.g., Twilio, MSG91)
    or a push-notification service. The architecture supports that drop-in.
  - The console print is intentional: it acts as the visible demo beat for
    the Agent Activity Log panel on the lawyer dashboard.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import CaseRecord


# ── Alert level thresholds ───────────────────────────────────────────────────

HIGH_URGENCY_THRESHOLD: int = 100   # scores above this → "HIGH" alert level


# ── Notification function ────────────────────────────────────────────────────

def trigger_notification(case: CaseRecord, urgency_score: int) -> dict:
    """
    Dispatch a simulated notification for a bail-eligible case and return
    a structured log record.

    Alert level rules:
        urgency_score > 100  → "HIGH"
        urgency_score <= 100 → "STANDARD"

    In the current implementation the dispatch is simulated via a console
    print. The return dict is what the orchestrator persists to the activity
    log and surfaces on the lawyer dashboard.

    Args:
        case:          A validated CaseRecord for an eligible prisoner.
        urgency_score: Integer score produced by the Prioritization Agent.

    Returns:
        A dict containing:
            case_id           — echoed from the input record
            status            — always "Notified" (simulated)
            alert_level       — "HIGH" or "STANDARD"
            timestamp         — ISO 8601 UTC timestamp of dispatch
            dispatched_message— the full alert string sent to the dashboard

    Example:
        >>> result = trigger_notification(case, urgency_score=267)
        >>> result["alert_level"]
        'HIGH'
        >>> result["status"]
        'Notified'
    """
    # ── 1. Determine alert level ─────────────────────────────────────────────
    alert_level = "HIGH" if urgency_score > HIGH_URGENCY_THRESHOLD else "STANDARD"

    # ── 2. Construct notification message ────────────────────────────────────
    message = (
        f"Alert [{alert_level}]: Case {case.case_id} ({case.name}) "
        f"is legally eligible for bail. "
        f"Urgency Score: {urgency_score}."
    )

    # ── 3. Simulate dispatch (console print) ─────────────────────────────────
    # NOTE: Replace this block with a real gateway call (Twilio / MSG91 / etc.)
    #       when moving to production. The function signature and return dict
    #       do not need to change.
    print("--- SIMULATED SMS DISPATCH ---")
    print(f"  To:      DLSA Lawyer Dashboard")
    print(f"  Message: {message}")
    print("------------------------------")

    # ── 4. Build and return structured log record ────────────────────────────
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    return {
        "case_id": case.case_id,
        "status": "Notified",
        "alert_level": alert_level,
        "timestamp": timestamp,
        "dispatched_message": message,
    }


# ── Standalone smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from app.models.schemas import UrgencyFlags

    # ── Case 1: High urgency — score 267 (above threshold of 100) ───────────
    case_high = CaseRecord(
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

    # ── Case 2: Standard urgency — score 60 (at or below threshold of 100) ──
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

    print("=" * 60)
    print("NOTIFICATION AGENT -- SMOKE TEST")
    print("=" * 60)

    test_cases = [
        ("Case 1 (High Urgency, score=267)", case_high, 267),
        ("Case 2 (Standard Urgency, score=60)", case_standard, 60),
    ]

    for label, case, score in test_cases:
        print(f"\n{label}")
        print("-" * 40)
        result = trigger_notification(case, urgency_score=score)
        print("\nReturned dict:")
        print(json.dumps(result, indent=2))

        # Assertions
        assert result["status"] == "Notified"
        assert result["case_id"] == case.case_id
        assert result["timestamp"] != ""

        if score > HIGH_URGENCY_THRESHOLD:
            assert result["alert_level"] == "HIGH", f"Expected HIGH, got {result['alert_level']}"
            assert "HIGH" in result["dispatched_message"]
            print("  [PASS] alert_level=HIGH, status=Notified")
        else:
            assert result["alert_level"] == "STANDARD", f"Expected STANDARD, got {result['alert_level']}"
            assert "STANDARD" in result["dispatched_message"]
            print("  [PASS] alert_level=STANDARD, status=Notified")

    print("\n" + "=" * 60)
    print("All smoke tests passed.")
    print("=" * 60)

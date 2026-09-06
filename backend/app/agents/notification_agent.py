"""
notification_agent.py Simulated alert dispatcher for Nyaya Mitra.

Design pattern (from Nyaya_Mitra_Master_Roadmap_v2.md §9, Agent 2.4):
  - This agent is EXPLICITLY SIMULATED no real SMS/email gateway is wired up.
  - In production this would integrate with an SMS gateway (e.g., Twilio, MSG91)
    or a push-notification service. The architecture supports that drop-in.
  - The console print is intentional: it acts as the visible demo beat for
    the Agent Activity Log panel on the lawyer dashboard.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import CaseRecord
from app.database import add_notification


# ── Alert level thresholds ───────────────────────────────────────────────────

HIGH_URGENCY_THRESHOLD: int = 100   # scores above this → "HIGH" alert level


# ── Notification function ────────────────────────────────────────────────────

def trigger_notification(
    case: CaseRecord,
    urgency_score: int,
    is_eligible: Optional[bool] = None,
) -> dict:
    """
    Dispatch a simulated notification for a bail-eligible case and return
    a structured log record.

    Alert level rules:
        urgency_score > 100  → "HIGH"
        urgency_score <= 100 → "STANDARD"

    Recipient resolution:
        - If assigned defense counsel exists: addresses counsel directly with role and district.
        - If unassigned: addresses both DLSA Legal Aid Desk and the Jail Superintendent.

    Factual eligibility check:
        - Accurately checks Section 479 BNSS eligibility. Ineligible cases (e.g. custody
          days below threshold) are flagged as pending threshold monitoring rather than
          falsely claiming legal bail eligibility.
    """
    from typing import Optional
    from app.agents.eligibility_agent import evaluate_eligibility

    # ── 1. Determine factual eligibility status ──────────────────────────────
    threshold_days = None
    if is_eligible is None:
        elig_result = evaluate_eligibility(case)
        is_eligible = bool(elig_result.get("eligible", False))
        threshold_days = elig_result.get("threshold_days")
    else:
        elig_result = evaluate_eligibility(case)
        threshold_days = elig_result.get("threshold_days")

    # ── 2. Determine alert level ─────────────────────────────────────────────
    alert_level = "HIGH" if urgency_score > HIGH_URGENCY_THRESHOLD else "STANDARD"

    # ── 3. Resolve dynamic recipient (No hardcoded DLSA) ─────────────────────
    assigned_lawyer = getattr(case, "assigned_lawyer", None)
    assigned_lawyer_id = getattr(case, "assigned_lawyer_id", None) or getattr(case, "assigned_advocate_id", None)
    jail_loc = getattr(case, "jail_location", None) or "Jail Custody Desk"
    dist = getattr(case, "district", None) or "District Legal Services"

    if assigned_lawyer or assigned_lawyer_id:
        recipient = f"Adv. {assigned_lawyer or 'Assigned Counsel'} (Defense Panel Counsel, {dist})"
        target_role = "DEFENSE_ADVOCATE,DLSA_OFFICER"
        target_user = assigned_lawyer_id
    else:
        recipient = f"DLSA Legal Aid Desk ({dist}) & Jail Superintendent ({jail_loc})"
        target_role = "DLSA_OFFICER,JAIL_OFFICER,SUPERVISING_LEGAL_OFFICER"
        target_user = None

    # ── 4. Construct factual message based on actual eligibility ─────────────
    if is_eligible:
        message = (
            f"Alert [{alert_level}]: Case {case.case_id} ({case.name}) "
            f"is legally eligible for bail under Section 479 BNSS. "
            f"Urgency Score: {urgency_score}."
        )

        # Simulate dispatch only for genuinely eligible cases
        print("--- SIMULATED SMS DISPATCH ---")
        print(f"  To:      {recipient}")
        print(f"  Message: {message}")
        print("------------------------------")

        # Save active alert to database
        notif_type = "urgent" if alert_level == "HIGH" else "info"
        title = "High Priority Bail Eligibility Flagged" if alert_level == "HIGH" else "Bail Eligibility Notice"
        add_notification(case.case_id, title, message, notif_type, target_role=target_role, user_id=target_user)
    else:
        custody_info = f"{case.custody_days}d served"
        if threshold_days:
            custody_info += f" of {threshold_days}d threshold"
        message = (
            f"Monitoring [{alert_level}]: Case {case.case_id} ({case.name}) "
            f"has not reached Section 479 BNSS detention threshold ({custody_info}). "
            f"Urgency Score: {urgency_score}."
        )

    # ── 5. Build and return structured log record ────────────────────────────
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

    # ── Case 1: High urgency score 267 (above threshold of 100) ───────────
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

    # ── Case 2: Standard urgency score 60 (at or below threshold of 100) ──
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

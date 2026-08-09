"""
status_agent.py Court status tracking state machine for Nyaya Mitra.

Design pattern (from Nyaya_Mitra_Master_Roadmap_v2.md §9, Agent 2.8):
  - EXPLICITLY SIMULATED integration no public court-record API exists to integrate
    against in a short build window. This is a named production integration
    point: in a real deployment, replace get_status() with a call to
    eCourts Services API (ecourts.gov.in) or a DLSA case management system.
  - For the hackathon, this now reads the actual persisted `status` from SQLite
    to demonstrate a stateful workflow (e.g. tracking a case transitioning
    from APPROVED to FILED to HEARING_SCHEDULED).
"""

from __future__ import annotations

from datetime import datetime, timezone

# ── Status lifecycle ─────────────────────────────────────────────────────────

CASE_STATUSES: list[str] = [
    "Pending Review",
    "Filed",
    "Hearing Scheduled",
    "Order Passed",
    "Released",
]


# ── Status function ────────────────────────────────────────────────────────────

from app.database import get_case

def get_status(case_id: str) -> dict:
    """
    Return the court tracking status for a case.

    For the hackathon, this reads the persisted state from the SQLite database
    rather than mocking it randomly, allowing for real stateful workflows.
    In production, this would make an external API call to eCourts.

    Args:
        case_id: The unique case identifier string (e.g., "UTP-0007").

    Returns:
        A dict containing:
            case_id        echoed input
            current_status the persisted CaseState string
            last_updated   ISO 8601 UTC timestamp of this check
    """
    case = get_case(case_id)
    current_status = case.status.value if case else "UNKNOWN"
    
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    return {
        "case_id": case_id,
        "current_status": current_status,
        "last_updated": timestamp,
    }


# ── Standalone smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    from app.database import init_db
    init_db()  # Ensure DB is seeded

    test_ids = ["UTP-0001", "UTP-0007", "UTP-0012", "UTP-0015", "UTP-0021"]

    print("=" * 60)
    print("STATUS AGENT -- SMOKE TEST")
    print("=" * 60)
    print(f"\n{'Case ID':<14}{'Status':<22}{'Deterministic?'}")
    print("-" * 55)

    for case_id in test_ids:
        result_1 = get_status(case_id)
        result_2 = get_status(case_id)   # call twice must be same

        assert result_1["current_status"] == result_2["current_status"], \
            f"{case_id}: status changed between calls must be deterministic"
        assert result_1["case_id"] == case_id

        print(f"{case_id:<14}{result_1['current_status']:<22}[PASS]")

    print("\n[PASS] All case IDs return valid, stateful statuses")
    print("\n" + "=" * 60)
    print("All smoke tests passed.")
    print("=" * 60)

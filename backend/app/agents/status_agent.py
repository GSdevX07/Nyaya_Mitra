"""
status_agent.py — Simulated court status tracking state machine for Nyaya Mitra.

Design pattern (from Nyaya_Mitra_Master_Roadmap_v2.md §9, Agent 2.8):
  - EXPLICITLY SIMULATED — no public court-record API exists to integrate
    against in a short build window. This is a named production integration
    point: in a real deployment, replace get_mock_status() with a call to
    eCourts Services API (ecourts.gov.in) or a DLSA case management system.
  - The status is derived deterministically from the case_id so the same
    case always returns the same status in the same session — makes demos
    reproducible without needing a database.
  - The five statuses model the real lifecycle a filed case goes through:
    Pending Review → Filed → Hearing Scheduled → Order Passed → Released
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


# ── Mock status function ─────────────────────────────────────────────────────

def get_mock_status(case_id: str) -> dict:
    """
    Return a simulated court tracking status for a case.

    The status is selected deterministically by hashing the case_id string,
    so the same case always maps to the same status — demos are reproducible
    without a database. Different case IDs spread across all five states,
    which makes the lawyer dashboard queue look realistic.

    NOTE: This is explicitly a simulation. The production integration point
    is a call to eCourts Services (ecourts.gov.in) or a DLSA case management
    system. Replace this function body only; the return schema is stable.

    Args:
        case_id: The unique case identifier string (e.g., "UTP-0007").

    Returns:
        A dict containing:
            case_id        — echoed input
            current_status — one of the five lifecycle stage strings
            last_updated   — ISO 8601 UTC timestamp of this simulated check

    Example:
        >>> result = get_mock_status("UTP-0007")
        >>> result["current_status"] in CASE_STATUSES
        True
    """
    # Deterministic selection: hash the case_id to an index in CASE_STATUSES
    status_index = hash(case_id) % len(CASE_STATUSES)
    current_status = CASE_STATUSES[status_index]
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    return {
        "case_id": case_id,
        "current_status": current_status,
        "last_updated": timestamp,
    }


# ── Standalone smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    test_ids = ["UTP-0001", "UTP-0007", "UTP-0012", "UTP-0015", "UTP-0021"]

    print("=" * 60)
    print("STATUS AGENT -- SMOKE TEST")
    print("=" * 60)
    print(f"\n{'Case ID':<14}{'Status':<22}{'Deterministic?'}")
    print("-" * 55)

    for case_id in test_ids:
        result_1 = get_mock_status(case_id)
        result_2 = get_mock_status(case_id)   # call twice — must be same

        assert result_1["current_status"] == result_2["current_status"], \
            f"{case_id}: status changed between calls — must be deterministic"
        assert result_1["current_status"] in CASE_STATUSES, \
            f"{case_id}: invalid status '{result_1['current_status']}'"
        assert result_1["case_id"] == case_id

        print(f"{case_id:<14}{result_1['current_status']:<22}[PASS]")

    print("\n[PASS] All case IDs return valid, deterministic statuses")
    print("\n" + "=" * 60)
    print("All smoke tests passed.")
    print("=" * 60)

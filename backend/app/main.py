"""
main.py — FastAPI application entry point for Nyaya Mitra.

Run locally:
    uvicorn app.main:app --reload --port 8000

Swagger docs available at:
    http://localhost:8000/docs

Design notes:
  - MOCK_DB is a module-level list of CaseRecord objects that acts as the
    in-memory database for the hackathon build. It contains 5 distinct hero
    cases covering every agent decision branch:
        UTP-0001  eligible first-time offender, all docs present   (HIGH priority)
        UTP-0007  eligible first-time, senior + health flag        (HIGHEST priority)
        UTP-0012  not yet eligible repeat offender                 (STANDARD)
        UTP-0015  eligible but missing a document                  (HIGH — docs gap)
        UTP-0021  eligible first-time, young + healthy             (STANDARD)
  - The human-approval gate (POST /cases/{id}/approve) is a real UI button,
    not a slide claim — matching the project ground rule from the roadmap.
  - process_case() is intentionally called only on individual case detail
    (GET /cases/{id}) so the queue endpoint remains fast even with many cases.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents.orchestrator import process_case
from app.agents.prioritization_agent import prioritize_cases
from app.models.schemas import CaseRecord, UrgencyFlags


# ── App initialisation ────────────────────────────────────────────────────────

app = FastAPI(
    title="Nyaya Mitra Backend API",
    description=(
        "Agentic AI Legal Operations API for Undertrial Prisoners. "
        "Built with synthetic data only — no real prisoner records are used."
    ),
    version="1.0.0",
)

# ── CORS (allow all origins for local hackathon dev) ─────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Mock database ─────────────────────────────────────────────────────────────
# 5 hero cases engineered to hit distinct agent decision branches.
# All data is synthetic — see Nyaya_Mitra_Master_Roadmap_v2.md §8, Step 1.1.

MOCK_DB: list[CaseRecord] = [

    # UTP-0001 — Eligible first-time offender, all docs present, young + healthy
    # Expected: eligible, complete, urgency=STANDARD
    CaseRecord(
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
    ),

    # UTP-0007 — Eligible first-time offender, senior citizen + health flag, all docs
    # Expected: eligible, complete, urgency=HIGH (score ~267)
    CaseRecord(
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
    ),

    # UTP-0012 — Not yet eligible repeat offender, missing docs
    # Expected: NOT eligible, NOT complete, draft skipped
    CaseRecord(
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
    ),

    # UTP-0015 — Eligible but missing a key document (tests Completeness Agent)
    # Expected: eligible, NOT complete (missing charge_sheet), draft skipped
    CaseRecord(
        case_id="UTP-0015",
        name="synthetic - not a real person",
        offense_sections=["IPC 392"],
        arrest_date="2023-03-01",
        custody_days=850,
        max_sentence_days_for_offense=1095,
        prior_bail_orders=["BAIL-2022-007"],
        required_docs=["remand_order", "charge_sheet", "prior_bail_order_if_any"],
        present_docs=["remand_order", "prior_bail_order_if_any"],
        urgency_flags=UrgencyFlags(age=40, health_flag=False, repeat_offender=True),
        jail_location="Central Jail, synthetic",
        preferred_language="kn",
    ),

    # UTP-0021 — Eligible first-time offender, elderly + health flag, all docs
    # Expected: eligible, complete, urgency=HIGH
    CaseRecord(
        case_id="UTP-0021",
        name="synthetic - not a real person",
        offense_sections=["IPC 420"],
        arrest_date="2024-06-20",
        custody_days=320,
        max_sentence_days_for_offense=730,
        prior_bail_orders=[],
        required_docs=["remand_order", "charge_sheet"],
        present_docs=["remand_order", "charge_sheet"],
        urgency_flags=UrgencyFlags(age=67, health_flag=True, repeat_offender=False),
        jail_location="District Jail, synthetic",
        preferred_language="te",
    ),
]

# Lookup index for O(1) case retrieval by case_id
_MOCK_DB_INDEX: dict[str, CaseRecord] = {c.case_id: c for c in MOCK_DB}


# ── Helper ────────────────────────────────────────────────────────────────────

def _find_case(case_id: str) -> CaseRecord:
    """Return the CaseRecord for case_id or raise a 404 HTTPException."""
    case = _MOCK_DB_INDEX.get(case_id)
    if not case:
        raise HTTPException(
            status_code=404,
            detail=f"Case '{case_id}' not found. Available IDs: {list(_MOCK_DB_INDEX.keys())}",
        )
    return case


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """Health check — confirms the API is online."""
    return {
        "status": "online",
        "service": "Nyaya Mitra API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "total_cases_in_db": len(MOCK_DB),
    }


@app.get("/cases", tags=["Cases"])
def get_cases():
    """
    Return all cases sorted by urgency score (highest first).

    Each item in the returned list includes the full CaseRecord, the
    computed days_overdue, and the urgency_score used for sorting.
    This is the primary data source for the lawyer dashboard queue.
    """
    # Build evaluation list with a fast approximation of days_overdue
    # (full Eligibility Agent is reserved for individual case detail)
    case_evaluations = []
    for case in MOCK_DB:
        days_overdue = max(
            0,
            case.custody_days - (case.max_sentence_days_for_offense // 2),
        )
        case_evaluations.append({
            "case": case,
            "days_overdue": days_overdue,
        })

    sorted_queue = prioritize_cases(case_evaluations)

    # Serialise CaseRecord objects to plain dicts for JSON response
    return [
        {
            "case": entry["case"].model_dump(),
            "days_overdue": entry["days_overdue"],
            "urgency_score": entry["urgency_score"],
        }
        for entry in sorted_queue
    ]


@app.get("/cases/{case_id}", tags=["Cases"])
def get_case_by_id(case_id: str):
    """
    Run the full 8-agent pipeline on a single case and return all outputs.

    Response includes:
      - eligibility, completeness, urgency_score, notification
      - retrieval, draft (if eligible + complete)
      - explanation (plain-language, in preferred language)
      - status_tracking, draft_ready flag
      - agent_activity_log (timestamped trace of every agent step)
    """
    case = _find_case(case_id)
    return process_case(case)


@app.post("/cases/{case_id}/approve", tags=["Cases"])
def approve_case(case_id: str):
    """
    Human-lawyer approval gate.

    This endpoint represents the mandatory sign-off that must happen before
    a bail application draft is considered 'filed'. It is a real UI button
    in the lawyer dashboard — not a slide claim.

    In production this would:
      - Record the approving lawyer's ID and timestamp in the database
      - Trigger the Status Tracking Agent to advance state to 'Filed'
      - Notify the Notification Agent to send a confirmation alert

    For the hackathon build, it returns a structured confirmation dict.
    """
    case = _find_case(case_id)
    return {
        "case_id": case_id,
        "status": "Approved by Human Lawyer",
        "next_step": "Status Tracking Agent will monitor court filing.",
        "offense_sections": case.offense_sections,
        "jail_location": case.jail_location,
    }

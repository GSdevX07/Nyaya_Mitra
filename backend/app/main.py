from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from app.models.schemas import CaseRecord

app = FastAPI(
    title="Nyaya Mitra Backend API",
    description="Agentic AI Legal Operations API for Undertrial Prisoners",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Nyaya Mitra API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/cases", response_model=List[CaseRecord])
def get_cases():
    # Mock synthetic cases
    return [
        CaseRecord(
            case_id="UTP-0007",
            name="synthetic - Ravi Kumar",
            offense_sections=["IPC 379", "BNSS Section 479"],
            arrest_date="2024-11-02",
            custody_days=410,
            max_sentence_days_for_offense=730,
            prior_bail_orders=[],
            required_docs=["remand_order", "charge_sheet", "prior_bail_order"],
            present_docs=["remand_order", "charge_sheet"],
            urgency_flags={"age": 63, "health_flag": True, "repeat_offender": False},
            jail_location="District Jail, synthetic",
            preferred_language="hi"
        )
    ]

@app.get("/cases/{case_id}", response_model=CaseRecord)
def get_case_by_id(case_id: str):
    return CaseRecord(
        case_id=case_id,
        name="synthetic - Ravi Kumar",
        offense_sections=["IPC 379", "BNSS Section 479"],
        arrest_date="2024-11-02",
        custody_days=410,
        max_sentence_days_for_offense=730,
        prior_bail_orders=[],
        required_docs=["remand_order", "charge_sheet", "prior_bail_order"],
        present_docs=["remand_order", "charge_sheet"],
        urgency_flags={"age": 63, "health_flag": True, "repeat_offender": False},
        jail_location="District Jail, synthetic",
        preferred_language="hi"
    )

@app.post("/cases/{case_id}/approve")
def approve_case(case_id: str):
    return {
        "case_id": case_id,
        "status": "APPROVED_FOR_FILING",
        "signed_by": "Legal Officer 104",
        "message": "Human review complete. Case queued for filing."
    }

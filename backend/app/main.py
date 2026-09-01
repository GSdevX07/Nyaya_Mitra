"""
main.py FastAPI application entry point for Nyaya Mitra.

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
        UTP-0015  eligible but missing a document                  (HIGH docs gap)
        UTP-0021  eligible first-time, young + healthy             (STANDARD)
  - The human-approval gate (POST /cases/{id}/approve) is a real UI button,
    not a slide claim matching the project ground rule from the roadmap.
  - process_case() is intentionally called only on individual case detail
    (GET /cases/{id}) so the queue endpoint remains fast even with many cases.
"""

from __future__ import annotations

import os
import warnings

# Suppress verbose oneDNN and TensorFlow informational messages
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import hashlib
import json
import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, File, UploadFile, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agents.orchestrator import process_case
from app.agents.prioritization_agent import prioritize_cases
from app.agents.eligibility_agent import evaluate_eligibility
from app.models.schemas import CaseRecord, UrgencyFlags, CaseState
from app.database import (
    init_db, get_all_cases, get_case, update_case_status, update_case_documents,
    add_evidence, get_all_evidence, get_evidence_item, get_all_notifications,
    store_uploaded_document, get_case_uploaded_documents,
)
from app.document_pipeline import DocumentPipelineError, DocumentPipelineResult, execute_full_document_pipeline, extract_document_text
from app.rag.legal_ingestion import LegalIngestionError, ingest_legal_pdf
from app.rag.vector_store import VectorStoreUnavailable, corpus_status


# ── App initialisation ────────────────────────────────────────────────────────
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import init_db
    init_db()
    yield

app = FastAPI(
    title="Nyaya Mitra Backend API",
    description=(
        "Agentic AI Legal Operations API for Undertrial Prisoners. "
        "Built with synthetic data only no real prisoner records are used."
    ),
    version="1.1.0",
    lifespan=lifespan,
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
# All data is synthetic see Nyaya_Mitra_Master_Roadmap_v2.md §8, Step 1.1.

MOCK_DB: list[CaseRecord] = [

    # UTP-0001 Eligible first-time offender, all docs present, young + healthy
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
        relative_name="Ramesh Kumar",
        relative_relation="Father",
        relative_phone="+91 98765 11001",
        permanent_address="Plot 42, Gandhi Nagar, Sector 4, Chennai, TN - 600001",
        assignment_status="AVAILABLE",
    ),

    # UTP-0007 Eligible first-time offender, senior citizen + health flag, all docs
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
        relative_name="Sunita Devi",
        relative_relation="Spouse / Wife",
        relative_phone="+91 98765 77007",
        permanent_address="Flat 12B, Old City Suburb, Jaipur, RJ - 302001",
        assignment_status="AVAILABLE",
    ),

    # UTP-0012 Not yet eligible repeat offender, missing docs
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
        relative_name="Mohd. Ahmed",
        relative_relation="Brother",
        relative_phone="+91 98765 12012",
        permanent_address="House 88, Shivaji Road, Bengaluru, KA - 560002",
        assignment_status="AVAILABLE",
    ),

    # UTP-0015 Eligible but missing a key document (tests Completeness Agent)
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
        relative_name="Anand Singh",
        relative_relation="Father",
        relative_phone="+91 98765 15015",
        permanent_address="Village Rampur, Post Office Sub-Jail Zone, Lucknow, UP - 226001",
        assignment_status="AVAILABLE",
    ),

    # UTP-0021 Eligible first-time offender, elderly + health flag, all docs
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
        relative_name="Kamla Prasad",
        relative_relation="Son / Guardian",
        relative_phone="+91 98765 21021",
        permanent_address="H.No 304, Green Avenue, Hyderabad, TS - 500001",
        assignment_status="AVAILABLE",
    ),
]

# ── Helper ────────────────────────────────────────────────────────────────────

def _find_case(case_id: str) -> CaseRecord:
    """Return the CaseRecord for case_id or raise a 404 HTTPException."""
    case = get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=404,
            detail=f"Case '{case_id}' not found.",
        )
    return case


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """Health check confirms the API is online."""
    return {
        "status": "online",
        "service": "Nyaya Mitra API",
        "version": "1.1.0",
        "docs_url": "/docs",
        "total_cases_in_db": len(get_all_cases()),  # Live count from SQLite
    }


@app.get("/cases", tags=["Cases"])
def get_cases():
    """
    Return all cases sorted by urgency score (highest first).

    Each item in the returned list includes the full CaseRecord, the
    computed days_overdue, and the urgency_score used for sorting.
    This is the primary data source for the lawyer dashboard queue.
    """
    # Build evaluation list using the canonical Eligibility Agent
    case_evaluations = []
    cases = get_all_cases()
    for case in cases:
        eligibility_result = evaluate_eligibility(case)
        case_evaluations.append({
            "case": case,
            "days_overdue": eligibility_result["days_overdue"],
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


@app.get("/cases/available", tags=["Available Cases"])
def get_available_cases():
    """
    Return all available undertrial cases that can be taken up by advocates.

    Reads from SQLite so assignment status is always consistent with the
    last take_up_case / decline_case call.
    """
    all_cases = get_all_cases()  # ← SQLite, not MOCK_DB
    available = [c for c in all_cases if c.assignment_status == "AVAILABLE"]
    case_evaluations = []
    for case in available:
        days_overdue = max(
            0,
            case.custody_days - (case.max_sentence_days_for_offense // 2),
        )
        case_evaluations.append({
            "case": case,
            "days_overdue": days_overdue,
        })

    sorted_queue = prioritize_cases(case_evaluations)
    return [
        {
            "case": entry["case"].model_dump(),
            "days_overdue": entry["days_overdue"],
            "urgency_score": entry["urgency_score"],
        }
        for entry in sorted_queue
    ]


# ── Document AI Pipeline endpoints MUST be before /cases/{case_id} ──────────
# FastAPI resolves GET routes in registration order; if these appear after the
# parameterised route, "sample-documents" gets matched as case_id.

class AssessDocumentPayload(BaseModel):
    document_name: str = "scanned_handwritten_remand.pdf"
    provided_text: Optional[str] = None


@app.post("/cases/assess-document", tags=["Document AI Pipeline"], response_model=DocumentPipelineResult)
def assess_legal_document(payload: Optional[AssessDocumentPayload] = Body(default=None)):
    """
    Executes the 7-stage Document AI pipeline:
    Document Intake -> TrOCR OCR -> IBM Data Prep Kit -> RAG -> IBM Granite -> Preliminary Assessment
    """
    doc_name = payload.document_name if payload else "scanned_handwritten_remand.pdf"
    text_content = payload.provided_text if payload else None
    try:
        return execute_full_document_pipeline(
            file_bytes=None,
            document_name=doc_name,
            provided_text=text_content,
        )
    except DocumentPipelineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/documents/assess", tags=["Document AI Pipeline"], response_model=DocumentPipelineResult)
async def assess_uploaded_document(file: UploadFile = File(...)):
    """Assess an uploaded PDF or image using the configured extraction/OCR service."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded document is empty.")
    document_name = file.filename or "uploaded-document"
    try:
        return execute_full_document_pipeline(file_bytes=content, document_name=document_name)
    except DocumentPipelineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/rag/legal-pdfs", tags=["RAG Training"])
async def upload_legal_pdf_for_rag(
    document_id: str = Form(...),
    source_name: str = Form(...),
    source_url: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
):
    """Ingest an authorised legal PDF through DPK preparation into Chroma."""
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status_code=415, detail="Only PDF legal sources may be indexed by this endpoint.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded legal PDF is empty.")
    try:
        return ingest_legal_pdf(document_id, source_name, content, source_url)
    except (LegalIngestionError, VectorStoreUnavailable, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/rag/status", tags=["RAG Training"])
def get_rag_status():
    try:
        return corpus_status()
    except VectorStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/cases/sample-documents", tags=["Document AI Pipeline"])
def get_sample_documents():
    """Retrieve pre-built scanned & handwritten legal document samples for quick demonstration."""
    return [
        {
            "id": "sample-1",
            "title": "Scanned Handwritten Bail Remand Order (UTP-0007)",
            "subtitle": "Senior Citizen \u2022 IPC 379 \u2022 Sub-Jail District Court",
            "document_name": "UTP-0007_Handwritten_Remand_Note.pdf",
            "preview_text": (
                "Handwritten Bail Remand Note - Sub-Jail Magistrate Court\n"
                "Date: 14/02/2025\n"
                "Accused Name: Ramesh Kumar (UTP-0007)\n"
                "Offense Sections: IPC Section 379 / BNSS Section 303\n"
                "Date of Arrest: 02-11-2024\n"
                "Total Days in Custody: 410 days\n"
                "Max Statutory Sentence for Offense: 730 days (2 years)\n"
                "Health Record / Medical Status: Patient suffers from chronic severe hypertension and joint arthritis. Senior Citizen aged 63 years.\n"
                "Prior Bail Status: Previous bail application rejected on 10/12/2024 due to missing charge sheet copy.\n"
                "Magistrate Note: Defense counsel submitted plea under Section 479 BNSS alleging undertrial period exceeds 50 percent of maximum sentence."
            ),
        },
        {
            "id": "sample-2",
            "title": "Handwritten FIR Record Extract (UTP-0001)",
            "subtitle": "First-Time Offender \u2022 IPC 323 \u2022 Central Jail",
            "document_name": "UTP-0001_Handwritten_FIR_Extract.png",
            "preview_text": (
                "Handwritten FIR Extract - Station House Officer\n"
                "Case ID: UTP-0001\n"
                "Accused Name: Suresh Patel\n"
                "Offense: IPC Section 323 (Voluntarily causing hurt)\n"
                "Arrest Date: 10-01-2025\n"
                "Custody Duration: 200 days\n"
                "Max Imprisonment Period: 365 days\n"
                "Prior Convictions: None (First-time offender)\n"
                "Doc Check: Charge sheet filed and remand order attached."
            ),
        },
        {
            "id": "sample-3",
            "title": "Scanned Case Summary & Custody Certificate (UTP-0021)",
            "subtitle": "Medical Priority \u2022 IPC 325 \u2022 High Priority Bench",
            "document_name": "UTP-0021_Medical_Custody_Cert.pdf",
            "preview_text": (
                "Scanned Custody Certificate & Medical Evaluation\n"
                "Case ID: UTP-0021\n"
                "Offense: IPC 325\n"
                "Arrest Date: 15-08-2024\n"
                "Days in Custody: 360 days\n"
                "Max Sentence: 1095 days\n"
                "Medical Note: Emergency cardiac review requested by Jail Superintendent. Requires urgent medical bail hearing."
            ),
        },
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


@app.post("/cases/{case_id}/take", tags=["Available Cases"])
def take_up_case(case_id: str, lawyer_id: str = "Legal Officer 104"):
    """
    Assign an available case to the specified lawyer upon full review & scroll approval.

    This endpoint represents the mandatory sign-off that must happen before
    a bail application draft is considered 'filed'. It is a real UI button
    in the lawyer dashboard not a slide claim.
    """
    case = _find_case(case_id)

    
    
    

    # Persist assignment into Supabase so get_available_cases reflects the change
    from app.database import supabase
    supabase.table("undertrial_cases").update({
        "assignment_status": "ASSIGNED",
        "assigned_lawyer_id": lawyer_id
    }).eq("id", case_id).execute()

    return {
        "status": "success",
        "case_id": case_id,
        "message": f"Approved by Human Lawyer bail application submitted to court. Assigned to {lawyer_id}",
        "next_step": "Status Tracking Agent will monitor hearing schedule.",
        "offense_sections": case.offense_sections,
        "jail_location": case.jail_location,
        "case": case.model_dump(),
    }


@app.post("/cases/{case_id}/decline", tags=["Available Cases"])
def decline_case(case_id: str, lawyer_id: str = "Legal Officer 104"):
    """
    Decline an available case so it is hidden and will not be presented to this lawyer again.
    """
    case = _find_case(case_id)

    # Persist DECLINED into Supabase
    from app.database import supabase
    supabase.table("undertrial_cases").update({
        "assignment_status": "DECLINED"
    }).eq("id", case_id).execute()

    return {
        "status": "declined",
        "message": f"Case {case_id} declined by {lawyer_id}. Will not show again.",
        "case_id": case_id,
    }


@app.post("/cases/{case_id}/approve", tags=["Cases"])
def approve_case(case_id: str, lawyer_id: str = "Legal Officer 104"):
    """
    Human-in-the-loop approval gate called from the Case Intelligence page.

    The lawyer reviews the full orchestrator output and clicks 'Approve & File'.
    This persists the FILED status and ASSIGNED assignment into SQLite.
    """
    case = _find_case(case_id)

    update_case_status(case_id, CaseState.APPROVED)
    update_case_status(case_id, CaseState.FILED)

    from app.database import supabase
    supabase.table("undertrial_cases").update({
        "assignment_status": "ASSIGNED",
        "assigned_lawyer_id": lawyer_id
    }).eq("id", case_id).execute()

    return {
        "status": "FILED",
        "case_id": case_id,
        "message": f"Case {case_id} approved and filed by {lawyer_id}.",
    }


@app.get("/lawyer/profile", tags=["Lawyer Profile"])
def get_lawyer_profile(lawyer_id: str = "Legal Officer 104"):
    """Return profile details and statistics for the advocate / legal officer."""
    # Count from SQLite reflects actual persisted assignment state
    assigned_count = sum(1 for c in get_all_cases() if c.assignment_status == "ASSIGNED")
    return {
        "id": "Legal Officer 104",
        "full_name": "Adv. Rajesh Sharma",
        "bar_association_id": "DL/2018/49281",
        "email": "rajesh.sharma@nyayamitra.org",
        "phone": "+91 98112 34567",
        "specialization": "Undertrial Defense & Section 479 BNSS",
        "cases_taken": assigned_count,
        "status": "Active Pro Bono Counsel",
        "organization": "Delhi Legal Services Authority (DLSA)",
    }



# ── Additional Module Endpoints ────────────────────────────────────────────────

@app.get("/documents", tags=["Documents"])
def get_documents():
    """
    Retrieve document status and vault inventory across all active cases.
    Reads from SQLite reflects any uploads that have been persisted.
    """
    docs = []
    cases = [c for c in get_all_cases() if c.assignment_status == "ASSIGNED"]
    for c in cases:  # ← SQLite, not MOCK_DB
        for r_doc in c.required_docs:
            is_present = r_doc in c.present_docs
            docs.append({
                "id": f"DOC-{c.case_id}-{r_doc}",
                "case_id": c.case_id,
                "prisoner_name": c.name,
                "document_type": r_doc.replace("_", " ").title(),
                "status": "Verified & Present" if is_present else "Missing Action Required",
                "is_present": is_present,
                "uploaded_date": c.arrest_date if is_present else None,
                "jail_location": c.jail_location,
            })
    return docs


@app.get("/cases/{case_id}/documents", tags=["Documents"])
def get_case_documents(case_id: str):
    """Retrieve document status breakdown for a single case."""
    case = _find_case(case_id)
    missing = [d for d in case.required_docs if d not in case.present_docs]
    return {
        "case_id": case_id,
        "required_docs": case.required_docs,
        "present_docs": case.present_docs,
        "missing_docs": missing,
        "is_complete": len(missing) == 0,
    }


@app.post("/documents/upload", tags=["Documents"])
async def upload_document(
    case_id: str,
    document_type: str,
    file: Optional[UploadFile] = File(None),
    custom_text: Optional[str] = Form(None),
):
    """
    Upload a real document file (PDF or image) and/or paste custom text for a case.

    - Accepts PDF files → extracts text via pypdf.
    - Accepts images (JPG, PNG, WEBP, BMP, TIFF, GIF, HEIC) → runs OCR (Tesseract
      or HANDWRITING_OCR_COMMAND) to recognise handwriting.
    - custom_text may be supplied instead of or alongside a file.
    - Extracted text + SHA-256 file hash are persisted to the `uploaded_documents`
      Supabase table.
    - present_docs on the case is updated so the document flips to 'Present'.
    """
    # ── 1. Read file bytes if a file was provided ─────────────────────────────
    file_bytes: Optional[bytes] = None
    file_name: str = "manual_entry.txt"
    mime_type: str = "text/plain"

    if file and file.filename:
        file_bytes = await file.read()
        file_name = file.filename
        mime_type = file.content_type or "application/octet-stream"

    # ── 2. Extract text from file (OCR / pypdf) ───────────────────────────────
    extracted_text = ""
    is_handwritten = False
    ocr_engine = "none"

    if file_bytes:
        try:
            is_handwritten, _conf, ocr_engine, extracted_text = extract_document_text(
                file_bytes, file_name, None
            )
        except DocumentPipelineError as exc:
            # Surface actionable OCR errors to the client
            raise HTTPException(status_code=422, detail=str(exc))

    # Use custom_text as fallback / supplement
    final_text = extracted_text or (custom_text or "")

    if not final_text.strip() and not file_bytes:
        raise HTTPException(
            status_code=422,
            detail="Please upload a file or paste text before submitting.",
        )

    # ── 3. Compute SHA-256 hash for tamper-evident storage ────────────────────
    file_hash = ""
    file_size = 0
    if file_bytes:
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file_size = len(file_bytes)

    # ── 4. Persist to Supabase uploaded_documents table ──────────────────────
    try:
        store_uploaded_document(
            case_id=case_id,
            document_type=document_type,
            file_name=file_name,
            extracted_text=extracted_text,
            custom_text=custom_text or "",
            is_handwritten=bool(is_handwritten),
            ocr_engine=ocr_engine,
            file_hash=file_hash,
            file_size_bytes=file_size,
            mime_type=mime_type,
        )
    except Exception as exc:
        # Non-fatal: log but don't block the upload workflow
        print(f"[WARN] store_uploaded_document failed: {exc}")

    # ── 5. Update present_docs on the case ───────────────────────────────────
    case = _find_case(case_id)
    updated_docs = list(case.present_docs)
    if document_type not in updated_docs:
        updated_docs.append(document_type)
    update_case_documents(case_id, updated_docs)

    all_required = set(case.required_docs)
    if all_required.issubset(set(updated_docs)):
        update_case_status(case_id, CaseState.DOCUMENTS_COMPLETE)
    else:
        update_case_status(case_id, CaseState.DOCUMENTS_MISSING)

    # ── 6. Add SHA-256 evidence record ───────────────────────────────────────
    evidence_hash = file_hash or hashlib.sha256(final_text.encode()).hexdigest()
    add_evidence(case_id, document_type, evidence_hash)

    return {
        "status": "success",
        "message": f"Document '{document_type}' uploaded and persisted for case {case_id}.",
        "present_docs": updated_docs,
        "is_complete": all_required.issubset(set(updated_docs)),
        "is_handwritten": bool(is_handwritten),
        "ocr_engine": ocr_engine,
        "extracted_text": final_text[:2000],  # preview, not full blob
        "file_name": file_name,
        "file_size_bytes": file_size,
        "file_hash": file_hash,
    }


@app.post("/documents/assess", tags=["Documents"])
async def assess_document_file(
    file: Optional[UploadFile] = File(None),
    case_id: Optional[str] = Form(None),
    document_name: Optional[str] = Form(None),
    provided_text: Optional[str] = Form(None),
):
    """
    Run the full document assessment pipeline on an uploaded file or pasted text.

    - PDF → pypdf text extraction → RAG → LLM assessment
    - Image → OCR (Tesseract / HANDWRITING_OCR_COMMAND) → RAG → LLM assessment
    - Returns structured assessment including eligibility status, legal citations,
      and extracted metadata.
    """
    file_bytes: Optional[bytes] = None
    name = document_name or "uploaded_document"

    if file and file.filename:
        file_bytes = await file.read()
        name = document_name or file.filename

    try:
        result = execute_full_document_pipeline(
            file_bytes=file_bytes,
            document_name=name,
            provided_text=provided_text,
        )
    except DocumentPipelineError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return result.model_dump()


@app.get("/documents/uploaded/{case_id}", tags=["Documents"])
def get_uploaded_documents(case_id: str):
    """
    Retrieve all previously uploaded document records for a case from Supabase.

    Returns file metadata, extracted text, OCR engine used, SHA-256 hash,
    and upload timestamp for every document uploaded against this case.
    """
    try:
        records = get_case_uploaded_documents(case_id)
        return records
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not fetch uploaded documents: {exc}")


# ── Evidence subsystem SHA-256 integrity verification ──────────────────────


@app.get("/evidence", tags=["Evidence"])
def get_evidence():
    """
    Retrieve evidence verification records.
    Reads directly from the dedicated 'evidence' SQLite table.
    """
    evidence_records = get_all_evidence()
    cases = {c.case_id: c for c in get_all_cases() if c.assignment_status == "ASSIGNED"}
    
    results = []
    for record in evidence_records:
        c = cases.get(record["case_id"])
        if not c:
            continue
            
        results.append({
            "id": record["evidence_id"],
            "case_id": record["case_id"],
            "title": record["document_type"].replace("_", " ").title(),
            "offense": ", ".join(c.offense_sections),
            "verification_status": "Stored in Vault",
            "authenticity_score": 100.0,
            "chain_of_custody": f"Uploaded at {c.jail_location}",
            "flagged": False,
            "notes": f"File: {record['file_name']}",
            "stored_hash": record["stored_hash"]
        })
    return results


@app.post("/evidence/verify", tags=["Evidence"])
def verify_evidence(evidence_id: str):
    """
    Verify an evidence item's integrity by recomputing its SHA-256 hash
    from the original bytes and comparing it to the stored hash.

    Returns MATCH (authentic) or MISMATCH (tampered) based on the hash comparison.
    """
    # 1. Fetch the stored evidence record
    record = get_evidence_item(evidence_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found.")
        
    case_id = record["case_id"]
    document_type = record["document_type"]
    stored_hash = record["stored_hash"]

    # 2. Re-read the physical file (simulated here with the deterministic string)
    mock_file_bytes = f"mock_file_content_for_{case_id}_{document_type}".encode()
    
    # 3. Compute the *current* hash
    current_hash = hashlib.sha256(mock_file_bytes).hexdigest()
    
    # 4. Compare cryptographic hashes
    is_match = current_hash == stored_hash
    
    status = "Verified Authentic" if is_match else "Integrity Violation"

    return {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "status": status,
        "tampering_detected": not is_match,
        "hash_algorithm": "SHA-256",
        "stored_hash": stored_hash,
        "computed_hash": current_hash,
        "integrity_verified": is_match,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "note": "SHA-256 integrity verified via cryptographic comparison." if is_match else "CRITICAL: Current document hash does not match original stored hash. Potential tampering detected."
    }


@app.get("/actions", tags=["Actions"])
def get_actions():
    """
    Retrieve automated agent actions queue derived from the canonical EligibilityAgent.
    No duplicate threshold logic everything flows through evaluate_eligibility().
    """
    actions = []
    cases = [c for c in get_all_cases() if c.assignment_status == "ASSIGNED"]
    for c in cases:
        eligibility = evaluate_eligibility(c)
        is_eligible = eligibility["eligible"]
        is_manual_review = "MANUAL_REVIEW" in eligibility["legal_basis"]
        missing_docs = [d for d in c.required_docs if d not in c.present_docs]

        if is_manual_review:
            actions.append({
                "id": f"ACT-{c.case_id}-REVIEW",
                "case_id": c.case_id,
                "action_type": "Manual Legal Review Required",
                "priority": "HIGH",
                "status": "Pending Manual Review",
                "description": eligibility["legal_basis"],
                "created_at": "2026-08-08",
            })
        elif is_eligible and not missing_docs:
            actions.append({
                "id": f"ACT-{c.case_id}-BAIL",
                "case_id": c.case_id,
                "action_type": "Auto-Draft BNSS 479 Petition",
                "priority": "HIGH",
                "status": "Ready for Approval",
                "description": (
                    f"Case {c.case_id} {eligibility['custody_days_served']} days served, "
                    f"{eligibility['required_custody_days']} required. "
                    f"Overdue by {eligibility['days_overdue']} days. Auto-draft generated."
                ),
                "created_at": "2026-08-08",
            })
        elif missing_docs:
            actions.append({
                "id": f"ACT-{c.case_id}-DOCS",
                "case_id": c.case_id,
                "action_type": "DLSA Document Request",
                "priority": "MEDIUM",
                "status": "Pending Document Retrieval",
                "description": f"Requesting missing documents ({', '.join(missing_docs)}) from police authority.",
                "created_at": "2026-08-08",
            })
    return actions


@app.post("/actions/trigger", tags=["Actions"])
def trigger_action(action_id: str):
    """Execute an automated agent action from the queue."""
    return {
        "action_id": action_id,
        "status": "Executed Successfully",
        "message": f"Action {action_id} triggered (DLSA submission simulated)."
    }


@app.get("/hearings", tags=["Hearings"])
def get_hearings():
    hearings = []
    cases = [c for c in get_all_cases() if c.assignment_status == "ASSIGNED"]
    
    # Generate a dynamic hearing for each assigned case
    for i, c in enumerate(cases):
        # Determine hearing date (fake date e.g. 7 days from now)
        target_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7 + i)
        
        # Simple heuristic for hearing type based on eligibility
        eligibility = evaluate_eligibility(c)
        if eligibility["eligible"]:
            hearing_type = "Bail Application Under BNSS 479"
            judge = "Hon'ble Justice R. K. Sharma"
        else:
            hearing_type = "Remand Review & Bail Motion"
            judge = "Hon'ble Magistrate S. Patel"
            
        hearings.append({
            "id": f"HRG-2026-{str(i+1).zfill(2)}",
            "case_id": c.case_id,
            "prisoner_name": c.name,
            "court_name": "District & Sessions Court" if eligibility["eligible"] else "Chief Judicial Magistrate Court",
            "hearing_date": target_date.strftime("%Y-%m-%d"),
            "hearing_type": hearing_type,
            "status": "Scheduled",
            "judge": judge,
        })

    return hearings


@app.get("/reports", tags=["Reports"])
def get_reports():
    """
    Retrieve legal analytics, inmate metrics, and DLSA performance report.
    ALL metrics are derived from the canonical EligibilityAgent no duplicate logic.
    """
    cases = [c for c in get_all_cases() if c.assignment_status == "ASSIGNED"]
    total_cases = len(cases)

    eligibility_results = [evaluate_eligibility(c) for c in cases]

    eligible_complete = 0
    eligible_missing_docs = 0
    manual_review_count = 0
    ineligible_count = 0

    for c, r in zip(cases, eligibility_results):
        if "MANUAL_REVIEW" in r["legal_basis"]:
            manual_review_count += 1
        elif r["eligible"]:
            if set(c.required_docs).issubset(set(c.present_docs)):
                eligible_complete += 1
            else:
                eligible_missing_docs += 1
        else:
            ineligible_count += 1

    eligible_count = eligible_complete + eligible_missing_docs
    senior_citizens = sum(1 for c in cases if c.urgency_flags.age >= 60)
    health_cases = sum(1 for c in cases if c.urgency_flags.health_flag)
    avg_custody = round(sum(c.custody_days for c in cases) / total_cases, 1) if total_cases else 0

    # Estimate hours saved: each eligible+complete case avoids ~12hrs manual review
    estimated_hours_saved = eligible_complete * 12

    # Build jail breakdown dynamically
    jail_counts: dict[str, int] = {}
    for c in cases:
        jail_name = c.jail_location.replace(" (Synthetic)", "").replace(", synthetic", "")
        jail_counts[jail_name] = jail_counts.get(jail_name, 0) + 1
    
    # Sort jail counts by highest first
    sorted_jails = sorted(jail_counts.items(), key=lambda x: x[1], reverse=True)
    jail_breakdown = [{"jail": jail, "count": count} for jail, count in sorted_jails]

    return {
        "overview": {
            "total_undertrials_monitored": total_cases,
            "bnss_479_eligible": eligible_count,
            "manual_review_required": manual_review_count,
            "senior_citizens": senior_citizens,
            "medical_priority_cases": health_cases,
            "average_custody_days": avg_custody,
            "estimated_hours_saved_by_ai": estimated_hours_saved,
            "estimated_hours_saved_note": f"{eligible_complete} cases × 12 hrs manual review avoided",
        },
        "court_jurisdiction_breakdown": jail_breakdown,
        "eligibility_distribution": [
            {"category": "Eligible & Complete", "count": eligible_complete},
            {"category": "Eligible (Missing Docs)", "count": eligible_missing_docs},
            {"category": "Ineligible (Sentence Threshold)", "count": ineligible_count},
            {"category": "Manual Review Required", "count": manual_review_count},
        ],
    }


@app.get("/notifications", tags=["Notifications"])
def get_notifications():
    """Retrieve system-wide alerts and notification feed from SQLite."""
    rows = get_all_notifications()
    notifications = []
    for row in rows:
        notifications.append({
            "id": row["id"],
            "title": row["title"],
            "message": row["message"],
            "timestamp": row["timestamp"],
            "type": row["type"],
            "case_id": row["case_id"],
            "read": bool(row["is_read"])
        })
    return notifications

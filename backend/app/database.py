"""
database.py Supabase PostgreSQL persistence for Nyaya Mitra.

This module provides a persistent state machine for the hackathon demo,
running on Supabase.
"""

import os
import datetime
from typing import List

from dotenv import load_dotenv
from supabase import create_client, Client
from pydantic import ValidationError

from app.models.schemas import CaseRecord, CaseState, UrgencyFlags

# Load environment variables
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db():
    """Create tables and seed initial mock data if empty.
    Handled externally via Supabase SQL editor or scripts now.
    """
    pass

def _map_row_to_case_record(row: dict) -> CaseRecord:
    try:
        flags = UrgencyFlags(
            age=row.get("age", 30),
            health_flag=row.get("health_flag", False),
            repeat_offender=not row.get("first_time_offender", True)
        )
        # Some rows might have "id" as the primary key from undertrial_cases
        case_id = row.get("id") or row.get("case_id")
        
        status_val = row.get("status", CaseState.DETECTED.value)
        # Ensure status is valid
        if status_val not in [s.value for s in CaseState]:
            status_val = CaseState.DETECTED.value
            
        case = CaseRecord(
            case_id=case_id,
            name=row.get("name", "Unknown"),
            offense_sections=row.get("offense_sections", []),
            arrest_date=row.get("arrest_date", "2023-01-01"),
            custody_days=row.get("custody_days", 0),
            max_sentence_days_for_offense=row.get("max_sentence_days_for_offense", 0),
            prior_bail_orders=row.get("prior_bail_orders", []),
            required_docs=row.get("required_docs", ["remand_order", "charge_sheet", "prior_bail_order_if_any"]),
            present_docs=row.get("present_docs", []),
            urgency_flags=flags,
            jail_location=row.get("jail_location", "Unknown"),
            preferred_language=row.get("preferred_language", "en"),
            relative_name=row.get("relative_name"),
            relative_relation=row.get("relative_relation"),
            relative_phone=row.get("relative_phone"),
            permanent_address=row.get("permanent_address"),
            assignment_status=row.get("assignment_status", "AVAILABLE"),
            assigned_lawyer_id=row.get("assigned_lawyer_id"),
            status=CaseState(status_val)
        )
        return case
    except Exception as e:
        print(f"Error mapping row to case record: {e} | Row: {row}")
        raise

def get_all_cases() -> List[CaseRecord]:
    """Retrieve all cases from the database."""
    # We fetch from 'undertrial_cases' instead of the deprecated 'cases' table.
    response = supabase.table("undertrial_cases").select("*").execute()
    cases = []
    for row in response.data:
        try:
            cases.append(_map_row_to_case_record(row))
        except Exception:
            pass
    return cases

def get_case(case_id: str) -> CaseRecord | None:
    """Retrieve a single case by ID."""
    response = supabase.table("undertrial_cases").select("*").eq("id", case_id).execute()
    if response.data:
        try:
            return _map_row_to_case_record(response.data[0])
        except Exception:
            pass
    return None


def update_case_status(case_id: str, new_status: CaseState) -> bool:
    """Update the status of a case. Returns True if successful."""
    # Update the row in undertrial_cases directly
    response = supabase.table("undertrial_cases").update({"status": new_status.value}).eq("id", case_id).execute()
    return len(response.data) > 0


def update_case_documents(case_id: str, present_docs: list) -> bool:
    """
    Persist an updated present_docs list for a case.
    This is required after document upload so the change survives a page reload.
    Returns True if successful.
    """
    response = supabase.table("undertrial_cases").update({"present_docs": present_docs}).eq("id", case_id).execute()
    return len(response.data) > 0


def add_evidence(case_id: str, document_type: str, stored_hash: str) -> str:
    """Insert a new evidence record and return the generated evidence_id."""
    evidence_id = f"EVI-{case_id}-{document_type}"
    file_name = f"{document_type}.pdf"
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Upsert (equivalent to REPLACE INTO)
    supabase.table("evidence").upsert({
        "evidence_id": evidence_id,
        "case_id": case_id,
        "document_type": document_type,
        "file_name": file_name,
        "stored_hash": stored_hash,
        "created_at": created_at
    }).execute()
    
    return evidence_id


def get_all_evidence() -> List[dict]:
    """Retrieve all evidence records."""
    response = supabase.table("evidence").select("*").execute()
    return response.data


def get_evidence_item(evidence_id: str) -> dict | None:
    """Retrieve a single evidence record by ID."""
    response = supabase.table("evidence").select("*").eq("evidence_id", evidence_id).execute()
    if response.data:
        return response.data[0]
    return None


def add_notification(case_id: str, title: str, message: str, notif_type: str) -> str:
    """Insert a new notification only if an identical one doesn't already exist.
    
    Uses a stable ID based on case_id + type to prevent duplicate notifications
    from being created every time a case detail page is loaded.
    """
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    notif_id = f"NOTIF-{case_id}-{notif_type}-{today}"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    try:
        # Ignore conflicts via 'on_conflict' on the primary key 'id'
        supabase.table("notifications").upsert({
            "id": notif_id,
            "case_id": case_id,
            "title": title,
            "message": message,
            "type": notif_type,
            "timestamp": timestamp,
            "is_read": 0
        }, on_conflict="id", ignore_duplicates=True).execute()
    except Exception as e:
        print(f"Error adding notification: {e}")
        
    return notif_id


def get_all_notifications() -> List[dict]:
    """Retrieve all notifications sorted by newest first."""
    response = supabase.table("notifications").select("*").order("timestamp", desc=True).execute()
    return response.data


def store_uploaded_document(
    case_id: str,
    document_type: str,
    file_name: str,
    extracted_text: str,
    custom_text: str,
    is_handwritten: bool,
    ocr_engine: str,
    file_hash: str,
    file_size_bytes: int,
    mime_type: str,
) -> str:
    """Upsert an uploaded document record into Supabase and return the document UUID.

    Uses an upsert keyed on (case_id, document_type) so re-uploading the same
    document type for the same case just refreshes the record rather than
    creating duplicates.
    """
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Build stable ID so we can upsert without a real duplicate
    import hashlib as _hashlib
    stable_id = _hashlib.md5(f"{case_id}-{document_type}".encode()).hexdigest()
    payload = {
        "id": stable_id,
        "case_id": case_id,
        "document_type": document_type,
        "file_name": file_name,
        "extracted_text": extracted_text,
        "custom_text": custom_text,
        "is_handwritten": is_handwritten,
        "ocr_engine": ocr_engine,
        "file_hash": file_hash,
        "file_size_bytes": file_size_bytes,
        "mime_type": mime_type,
        "uploaded_at": created_at,
    }
    supabase.table("uploaded_documents").upsert(payload, on_conflict="id").execute()
    return stable_id


def get_case_uploaded_documents(case_id: str) -> List[dict]:
    """Retrieve all uploaded document records for a given case."""
    response = (
        supabase.table("uploaded_documents")
        .select("*")
        .eq("case_id", case_id)
        .order("uploaded_at", desc=True)
        .execute()
    )
    return response.data


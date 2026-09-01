"""
supabase_adapter.py — Production Supabase PostgreSQL Repository Adapter for Nyaya Mitra.

This adapter replaces the local SQLite path for all production/cloud operations.
When SUPABASE_URL and SUPABASE_SERVICE_KEY are set in .env, this is activated.
The SQLite backend remains as local development / demo fallback.

How to activate:
  1. Run supabase_stage02_migration.sql in your Supabase SQL Editor.
  2. Set SUPABASE_URL and SUPABASE_SERVICE_KEY in backend/.env (NOT .env.example).
  3. Restart the backend.

All data operations will then route through Supabase PostgreSQL.
"""

from __future__ import annotations
import os
import datetime
import json
from typing import List, Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

_supabase = None


def get_supabase_client():
    """Return a live Supabase client, or None if not configured."""
    global _supabase
    if _supabase is not None:
        return _supabase
    if SUPABASE_URL and SUPABASE_KEY and not SUPABASE_URL.startswith("https://your-project-ref"):
        try:
            from supabase import create_client
            _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            print(f"[INFO] Supabase PostgreSQL adapter active: {SUPABASE_URL.split('.supabase.co')[0]}...")
            return _supabase
        except Exception as e:
            print(f"[WARN] Supabase client init failed: {e}. Backend will use SQLite fallback.")
    return None


def is_supabase_active() -> bool:
    """Returns True when a live Supabase client is available."""
    return get_supabase_client() is not None


# ── Organization Queries ──────────────────────────────────────────────────────

def supa_get_all_organizations() -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    res = client.table("organizations").select("*").eq("is_active", True).execute()
    return res.data or []


def supa_get_organization(org_id: str) -> Optional[Dict]:
    client = get_supabase_client()
    if not client:
        return None
    res = client.table("organizations").select("*").eq("id", org_id).single().execute()
    return res.data


# ── Accused Persons Queries ───────────────────────────────────────────────────

def supa_get_accused_person(accused_id: str) -> Optional[Dict]:
    client = get_supabase_client()
    if not client:
        return None
    res = client.table("accused_persons").select("*").eq("id", accused_id).single().execute()
    return res.data


def supa_upsert_accused_person(accused: Dict) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    accused["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    client.table("accused_persons").upsert(accused).execute()
    return True


# ── Court Cases Queries ──────────────────────────────────────────────────────

def supa_get_all_court_cases() -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    res = (
        client.table("court_cases")
        .select("*, accused_persons(*), charges(*)")
        .is_("deleted_at", "null")
        .execute()
    )
    return res.data or []


def supa_get_court_case(case_id: str) -> Optional[Dict]:
    client = get_supabase_client()
    if not client:
        return None
    res = (
        client.table("court_cases")
        .select("*, accused_persons(*), firs(*), charges(*), custody_records(*), documents(*)")
        .eq("id", case_id)
        .single()
        .execute()
    )
    return res.data


def supa_update_case_status(case_id: str, new_status: str, actor_id: str = "system") -> bool:
    client = get_supabase_client()
    if not client:
        return False
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    client.table("court_cases").update({
        "current_status": new_status,
        "updated_at": now_iso,
    }).eq("id", case_id).execute()
    # Sync legacy cases table
    client.table("cases").update({
        "status": new_status,
        "updated_at": now_iso,
    }).eq("case_id", case_id).execute()
    return True


def supa_update_case_assignment(case_id: str, lawyer_id: str, status: str = "ASSIGNED") -> bool:
    client = get_supabase_client()
    if not client:
        return False
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    client.table("court_cases").update({
        "assigned_lawyer_id": lawyer_id,
        "assignment_status": status,
        "updated_at": now_iso,
    }).eq("id", case_id).execute()
    # Sync legacy
    client.table("cases").update({
        "assigned_lawyer_id": lawyer_id,
        "assignment_status": status,
        "updated_at": now_iso,
    }).eq("case_id", case_id).execute()
    return True


# ── Legacy Cases Table (Backward Compatibility) ───────────────────────────────

def supa_get_all_legacy_cases() -> List[Dict]:
    """Fetch the full JSON blob-based cases for backward-compatible API endpoints."""
    client = get_supabase_client()
    if not client:
        return []
    res = client.table("cases").select("data").execute()
    return [row["data"] for row in (res.data or []) if row.get("data")]


def supa_upsert_legacy_case(case_id: str, data: Dict, status: str, assignment_status: str, assigned_lawyer_id: Optional[str]) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    client.table("cases").upsert({
        "case_id": case_id,
        "data": data,
        "status": status,
        "assignment_status": assignment_status,
        "assigned_lawyer_id": assigned_lawyer_id,
        "updated_at": now_iso,
    }).execute()
    return True


# ── Evidence & Documents Queries ──────────────────────────────────────────────

def supa_get_all_evidence() -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    res = client.table("evidence").select("*").execute()
    return res.data or []


def supa_get_case_evidence(case_id: str) -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    res = client.table("evidence").select("*").eq("case_id", case_id).execute()
    return res.data or []


def supa_upsert_evidence(record: Dict) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    client.table("evidence").upsert(record).execute()
    return True


def supa_get_case_documents(case_id: str) -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    res = client.table("uploaded_documents").select("*").eq("case_id", case_id).execute()
    return res.data or []


def supa_save_uploaded_document(record: Dict) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    client.table("uploaded_documents").upsert(record).execute()
    return True


# ── Notifications Queries ─────────────────────────────────────────────────────

def supa_get_all_notifications() -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    res = client.table("notifications").select("*").order("timestamp", desc=True).execute()
    return res.data or []


def supa_add_notification(record: Dict) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    client.table("notifications").upsert(record).execute()
    return True


# ── Audit Events Queries ──────────────────────────────────────────────────────

def supa_append_audit_event(event: Dict) -> bool:
    """Insert an immutable audit event into PostgreSQL. Protected by DB-level trigger."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.table("audit_events").insert(event).execute()
        return True
    except Exception as e:
        print(f"[WARN] Supabase audit event write failed: {e}")
        return False


def supa_get_entity_audit_trail(entity_type: str, entity_id: str) -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    res = (
        client.table("audit_events")
        .select("*")
        .eq("entity_type", entity_type)
        .eq("entity_id", entity_id)
        .order("timestamp", desc=True)
        .execute()
    )
    return res.data or []

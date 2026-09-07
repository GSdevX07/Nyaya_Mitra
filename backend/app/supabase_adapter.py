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
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("nyaya_mitra.supabase_adapter")

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


def assert_production_db_available():
    """Ensure production does not silently operate with missing primary database."""
    app_env = os.environ.get("APP_ENV", "development").lower()
    if app_env == "production" and not is_supabase_active():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Authoritative PostgreSQL database is currently unavailable in production.",
        )


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
    rec = dict(record)
    if "is_read" in rec:
        rec["is_read"] = bool(rec["is_read"])
    client.table("notifications").upsert(rec).execute()
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
        err_str = str(e)
        # If remote Supabase schema cache has not yet migrated newly added columns, filter down to legacy columns
        if any(c in err_str for c in ["event_hash", "previous_event_hash", "hash_algorithm", "sequence_number", "severity", "data_status"]):
            try:
                legacy_cols = {
                    "id", "timestamp", "actor_id", "actor_role", "organization_id",
                    "action", "entity_type", "entity_id", "ip_address", "details_json", "is_immutable"
                }
                fallback_event = {k: v for k, v in event.items() if k in legacy_cols}
                client.table("audit_events").insert(fallback_event).execute()
                return True
            except Exception as inner_e:
                print(f"[WARN] Supabase audit event write fallback failed: {inner_e}")
        else:
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


def supa_get_all_audit_events(limit: int = 50) -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    res = (
        client.table("audit_events")
        .select("*")
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


# ── Family Contacts Queries ───────────────────────────────────────────────────

def supa_get_family_contacts(accused_id: str) -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    res = (
        client.table("family_contacts")
        .select("*")
        .eq("accused_id", accused_id)
        .order("is_primary_contact", desc=True)
        .execute()
    )
    return res.data or []


# ── Hearings Schedule Queries ─────────────────────────────────────────────────

def supa_get_hearings_schedule() -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    res = (
        client.table("hearings_schedule")
        .select("*")
        .order("hearing_date", desc=False)
        .execute()
    )
    return res.data or []


# ── Identity Merge Candidates Queries ─────────────────────────────────────────

def supa_get_identity_merge_candidates(status_filter: Optional[str] = "PENDING_HUMAN_REVIEW") -> List[Dict]:
    client = get_supabase_client()
    if not client:
        return []
    try:
        q = client.table("identity_merge_candidates").select("*")
        if status_filter and status_filter.upper() != "ALL":
            q = q.eq("review_status", status_filter)
        res = q.order("match_confidence", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"[WARN] supa_get_identity_merge_candidates error: {e}")
        return []


def supa_resolve_merge_candidate(candidate_id: str, action: str, notes: str, reviewed_by: str) -> Optional[Dict]:
    client = get_supabase_client()
    if not client:
        return None
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    client.table("identity_merge_candidates").update({
        "review_status": action,
        "reviewed_by": reviewed_by,
        "reviewed_at": now_iso,
        "resolution_notes": notes,
    }).eq("id", candidate_id).execute()
    res = client.table("identity_merge_candidates").select("*").eq("id", candidate_id).single().execute()
    return res.data


def supa_get_identity_references(accused_id: str) -> Dict[str, str]:
    client = get_supabase_client()
    if not client:
        return {}
    try:
        res = client.table("identity_references").select("*").eq("accused_id", accused_id).execute()
        if res.data:
            out = {}
            for row in res.data:
                id_type = row.get("id_type")
                id_val = row.get("id_value")
                if id_type and id_val:
                    out[id_type] = id_val
            return out
    except Exception:
        pass
    return {}


def supa_get_case_documents_with_visibility(case_id: str, audience: str = "citizen") -> List[Dict]:
    """Retrieve case documents filtered by audience visibility."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        query = client.table("uploaded_documents").select("*").eq("case_id", case_id)
        if audience == "citizen":
            query = query.eq("citizen_visible", True)
        elif audience == "family":
            query = query.eq("family_visible", True)
        res = query.execute()
        return res.data or []
    except Exception:
        return []


def supa_log_document_access(record: Dict) -> bool:
    """Insert document access log into PostgreSQL."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.table("document_access_logs").insert(record).execute()
        return True
    except Exception as e:
        # Table might not exist yet if migration has not run
        return False


def supa_record_field_correction(record: Dict) -> bool:
    """Insert document field correction into PostgreSQL."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.table("document_field_corrections").insert(record).execute()
        return True
    except Exception as e:
        return False


def supa_store_document_version(record: Dict) -> bool:
    """Insert document processing version into PostgreSQL."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.table("document_processing_versions").insert(record).execute()
        return True
    except Exception as e:
        return False


def supa_add_police_action(record: Dict) -> bool:
    """Insert police operational action into PostgreSQL."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.table("police_actions").insert(record).execute()
        return True
    except Exception as e:
        return False


def supa_update_police_action(action_id: str, updates: Dict) -> bool:
    """Update police operational action in PostgreSQL."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.table("police_actions").update(updates).eq("id", action_id).execute()
        return True
    except Exception as e:
        return False


# ── Operational Task Queue Queries & Mutations ──────────────────────────────

def supa_get_task_queue(
    current_user_role: str,
    user_id: str,
    user_facilities: List[str],
    user_district: Optional[str],
    linked_case_id: Optional[str],
    police_station: Optional[str] = None,
    facility: Optional[str] = None,
    district: Optional[str] = None,
    priority: Optional[str] = None,
    custody_duration_min: Optional[int] = None,
    document_completeness_max: Optional[int] = None,
    legal_aid_need: Optional[bool] = None,
    hearing_date_from: Optional[str] = None,
    hearing_date_to: Optional[str] = None,
    has_data_conflict: Optional[bool] = None,
    assignment_status: Optional[str] = None,
    matter_status: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "due_date",
    sort_order: Optional[str] = "asc",
) -> List[Dict]:
    """
    Retrieve task queue items directly from authoritative Supabase PostgreSQL table.
    Enforces strict role boundaries and dynamic filter criteria.
    """
    client = get_supabase_client()
    if not client:
        return []

    q = client.table("task_queue").select("*")

    # 1. Role boundaries
    if current_user_role == "JAIL_OFFICER":
        q = q.eq("owner_role", "JAIL_OFFICER")
        if user_facilities:
            q = q.in_("facility", user_facilities)
    elif current_user_role in ("DEFENSE_ADVOCATE", "CONTROLLED_EXTERNAL_ADVOCATE"):
        q = q.eq("owner_role", "DEFENSE_ADVOCATE").eq("assignment_status", "ASSIGNED")
        if user_id in ("demo_advocate", "adv_001", "adv_rajesh_sharma"):
            q = q.in_("owner_user_id", ["demo_advocate", "adv_001", "adv_rajesh_sharma"])
        elif user_id in ("demo_ext_advocate", "adv_ext_001"):
            q = q.in_("owner_user_id", ["demo_ext_advocate", "adv_ext_001"])
        else:
            q = q.eq("owner_user_id", user_id)
    elif current_user_role == "DLSA_OFFICER":
        q = q.in_("owner_role", ["DLSA_OFFICER", "SUPERVISING_LEGAL_OFFICER"])
        if user_district:
            q = q.eq("district", user_district)
    elif current_user_role == "SUPERVISING_LEGAL_OFFICER":
        q = q.in_("owner_role", ["SUPERVISING_LEGAL_OFFICER", "DLSA_OFFICER"])
        if user_district:
            q = q.eq("district", user_district)
    elif current_user_role == "POLICE_OFFICER":
        if police_station:
            q = q.eq("facility", police_station)
        else:
            return []
    elif current_user_role in ("ACCUSED_USER", "FAMILY_GUARDIAN"):
        if linked_case_id:
            q = q.eq("case_id", linked_case_id)
        else:
            return []

    # 2. Dynamic filters
    if facility:
        q = q.ilike("facility", f"%{facility}%")
    if district:
        q = q.ilike("district", f"%{district}%")
    if priority:
        q = q.eq("priority", priority.upper())
    if custody_duration_min is not None:
        q = q.gte("custody_duration_days", custody_duration_min)
    if document_completeness_max is not None:
        q = q.lte("document_completeness_pct", document_completeness_max)
    if legal_aid_need is not None:
        q = q.eq("legal_aid_need", 1 if legal_aid_need else 0)
    if has_data_conflict is not None:
        q = q.eq("has_data_conflict", 1 if has_data_conflict else 0)
    if assignment_status:
        q = q.eq("assignment_status", assignment_status.upper())
    if matter_status:
        q = q.eq("matter_status", matter_status.upper())

    today_iso = datetime.date.today().isoformat()
    if status:
        if status.upper() == "OVERDUE":
            q = q.neq("status", "COMPLETED").lt("due_date", today_iso)
        else:
            q = q.eq("status", status.upper())

    # Order
    is_desc = (sort_order or "").lower() == "desc"
    order_col = sort_by if sort_by in ("due_date", "priority", "custody_duration_days", "created_at", "status") else "due_date"
    q = q.order(order_col, desc=is_desc)

    res = q.execute()
    items = res.data or []

    # Post-filtering for advocate preliminary state exclusions & search
    results = []
    for d in items:
        if current_user_role in ("DEFENSE_ADVOCATE", "CONTROLLED_EXTERNAL_ADVOCATE"):
            m_st = d.get("matter_status") or ""
            if m_st in ('INTAKE', 'INTAKE_PENDING', 'DETECTED', 'VERIFICATION', 'CUSTODY_VERIFIED', 'CUSTODY_PENDING', 'REVIEW', 'LEGAL_AID_REQUIRED', 'LEGAL_NEED_IDENTIFIED', 'PRE_INTAKE', 'DOCUMENTS_MISSING', 'DRAFT_INTAKE'):
                continue

        if d.get("status") not in ("COMPLETED", "EXCEPTION") and d.get("due_date") and d["due_date"] < today_iso:
            d["status"] = "OVERDUE"

        if search:
            s = search.strip().lower()
            t_title = (d.get("title") or "").lower()
            t_reason = (d.get("reason") or "").lower()
            t_acc = (d.get("accused_name") or "").lower()
            t_cid = (d.get("case_id") or "").lower()
            if not (s in t_title or s in t_reason or s in t_acc or s in t_cid):
                continue

        results.append(d)

    return results


def supa_get_task_by_id(task_id: str) -> Optional[Dict]:
    """Fetch single task from Supabase PostgreSQL."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        res = client.table("task_queue").select("*").eq("id", task_id).single().execute()
        return res.data
    except Exception:
        return None


def supa_upsert_task_queue_items(tasks: List[Dict]) -> bool:
    """Upsert batch of operational tasks directly into Supabase PostgreSQL."""
    client = get_supabase_client()
    if not client or not tasks:
        return False
    try:
        chunk_size = 100
        for i in range(0, len(tasks), chunk_size):
            chunk = tasks[i:i + chunk_size]
            client.table("task_queue").upsert(chunk).execute()
        return True
    except Exception as e:
        logger.warning(f"supa_upsert_task_queue_items error: {e}")
        return False


def supa_update_task(task_id: str, updates: Dict) -> Optional[Dict]:
    """Update single task in Supabase PostgreSQL."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        res = client.table("task_queue").update(updates).eq("id", task_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.warning(f"supa_update_task error: {e}")
        return None


def supa_bulk_update_tasks(task_ids: List[str], updates: Dict) -> int:
    """Bulk update tasks in Supabase PostgreSQL."""
    client = get_supabase_client()
    if not client or not task_ids:
        return 0
    try:
        res = client.table("task_queue").update(updates).in_("id", task_ids).execute()
        return len(res.data or [])
    except Exception as e:
        logger.warning(f"supa_bulk_update_tasks error: {e}")
        return 0


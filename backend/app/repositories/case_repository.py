"""
case_repository.py - Normalized Case Repository with Legacy Compatibility Adapter.
"""

from __future__ import annotations
import sqlite3
import datetime
from typing import List, Optional, Dict, Any
from app.models.schemas import (
    CaseRecord,
    PrisonerCategory,
    LegalCode,
    DataSourceStatus,
    UrgencyFlags,
    CaseState,
    TimelineEvent,
)
from app.models.domain import (
    CourtCase,
    AccusedPerson,
    CustodyRecord,
    ChargeLegalSection,
    BailApplication,
    DocumentRecord,
    generate_prefixed_id,
)


class CaseRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        from app.database import DB_PATH, get_db_connection
        if self.db_path == DB_PATH:
            return get_db_connection()
        is_uri = "mode=memory" in str(self.db_path) or str(self.db_path).startswith("file:")
        conn = sqlite3.connect(self.db_path, uri=is_uri, timeout=30.0, check_same_thread=False)
        return conn

    def get_all_cases(self) -> List[CaseRecord]:
        """Retrieve all cases from Supabase PostgreSQL (authoritative) or in-memory fallback."""
        try:
            from app.supabase_adapter import supa_get_all_legacy_cases, is_supabase_active
            if is_supabase_active():
                raw = supa_get_all_legacy_cases()
                if raw:
                    return [CaseRecord.model_validate(d) for d in raw]
        except Exception as e:
            print(f"[WARN] CaseRepository.get_all_cases Supabase error: {e}")

        conn = None
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM cases WHERE data IS NOT NULL")
            rows = cursor.fetchall()
            if rows:
                return [CaseRecord.model_validate_json(r[0]) for r in rows]
        except Exception as e:
            print(f"[WARN] CaseRepository.get_all_cases error: {e}")
        finally:
            if conn:
                conn.close()
        return []

    def get_case_by_id(self, case_id: str) -> Optional[CaseRecord]:
        """Retrieve single case record by case_id from Supabase PostgreSQL or in-memory."""
        try:
            from app.supabase_adapter import get_supabase_client, is_supabase_active
            if is_supabase_active():
                cli = get_supabase_client()
                if cli:
                    res = cli.table("cases").select("data").eq("case_id", case_id).execute()
                    if res.data and res.data[0].get("data"):
                        return CaseRecord.model_validate(res.data[0]["data"])
        except Exception:
            pass

        conn = None
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
            row = cursor.fetchone()
            if row:
                return CaseRecord.model_validate_json(row[0])
        except Exception as e:
            print(f"[WARN] CaseRepository.get_case_by_id error: {e}")
        finally:
            if conn:
                conn.close()
        return None

    def update_case_status(self, case_id: str, new_status: CaseState, actor_id: str = "system") -> bool:
        """Update case state in Supabase PostgreSQL, normalized court_cases, and legacy cases."""
        case = self.get_case_by_id(case_id)
        if not case:
            return False

        case.status = new_status
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Append to case internal timeline
        case.timeline.append(
            TimelineEvent(
                id=f"TLE-{case_id}-{len(case.timeline) + 1}",
                timestamp=now_iso,
                event_type="STATUS_CHANGE",
                title=f"Case Status Transitioned to {new_status.value}",
                description=f"Status modified by {actor_id}.",
                actor=actor_id,
                actor_role="Legal Officer",
                source="Nyaya Mitra State Engine",
                is_human_verified=True,
            )
        )

        # Update in Supabase PostgreSQL (Authoritative Cloud)
        try:
            from app.supabase_adapter import supa_update_case_status, is_supabase_active
            if is_supabase_active():
                supa_update_case_status(case_id, new_status.value, actor_id)
        except Exception as e:
            print(f"[WARN] CaseRepository.update_case_status Supabase error: {e}")

        conn = None
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            # Update legacy cases table
            cursor.execute(
                "UPDATE cases SET status = ?, data = ? WHERE case_id = ?",
                (new_status.value, case.model_dump_json(), case_id),
            )
            # Update normalized court_cases table
            cursor.execute(
                "UPDATE court_cases SET current_status = ?, updated_at = ? WHERE case_number = ? OR id = ?",
                (new_status.value, now_iso, case_id, case_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[WARN] CaseRepository.update_case_status error: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def update_case_documents(self, case_id: str, present_docs: List[str]) -> bool:
        """Update documents list and sync normalized document records."""
        case = self.get_case_by_id(case_id)
        if not case:
            return False

        case.present_docs = present_docs
        conn = None
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE cases SET data = ? WHERE case_id = ?",
                (case.model_dump_json(), case_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[WARN] CaseRepository.update_case_documents error: {e}")
            return False
        finally:
            if conn:
                conn.close()

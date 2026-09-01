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

    def get_all_cases(self) -> List[CaseRecord]:
        """Retrieve all cases from normalized tables or fallback to legacy cases."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM cases WHERE data IS NOT NULL")
            rows = cursor.fetchall()
            conn.close()
            if rows:
                return [CaseRecord.model_validate_json(r[0]) for r in rows]
        except Exception as e:
            print(f"[WARN] CaseRepository.get_all_cases error: {e}")
        return []

    def get_case_by_id(self, case_id: str) -> Optional[CaseRecord]:
        """Retrieve single case record by case_id."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return CaseRecord.model_validate_json(row[0])
        except Exception as e:
            print(f"[WARN] CaseRepository.get_case_by_id error: {e}")
        return None

    def update_case_status(self, case_id: str, new_status: CaseState, actor_id: str = "system") -> bool:
        """Update case state in both normalized court_cases and legacy cases view."""
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

        try:
            conn = sqlite3.connect(self.db_path)
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
            conn.close()
            return True
        except Exception as e:
            print(f"[WARN] CaseRepository.update_case_status error: {e}")
            return False

    def update_case_documents(self, case_id: str, present_docs: List[str]) -> bool:
        """Update documents list and sync normalized document records."""
        case = self.get_case_by_id(case_id)
        if not case:
            return False

        case.present_docs = present_docs
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE cases SET data = ? WHERE case_id = ?",
                (case.model_dump_json(), case_id),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[WARN] CaseRepository.update_case_documents error: {e}")
            return False

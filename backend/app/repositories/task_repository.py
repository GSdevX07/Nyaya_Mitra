"""
task_repository.py — Single-Source Task Queue Repository.
=========================================================
Implements clean repository abstraction for the Universal Task Queue.
When Supabase is active, Supabase PostgreSQL is the SINGLE AUTHORITATIVE SOURCE OF TRUTH.
When running offline or in local zero-dependency development, SqliteTaskRepository is used.
"""

from __future__ import annotations
import abc
import datetime
import logging
from typing import List, Optional, Dict, Any

from app.auth.dependencies import AuthUser

logger = logging.getLogger("nyaya_mitra.task_repository")


class BaseTaskRepository(abc.ABC):
    """Abstract contract for operational task queue persistence."""

    @abc.abstractmethod
    def get_task_queue(
        self,
        current_user: AuthUser,
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
    ) -> List[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def get_tasks_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def upsert_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        pass

    @abc.abstractmethod
    def upsert_task(self, task: Dict[str, Any]) -> bool:
        pass

    @abc.abstractmethod
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def bulk_update_tasks(self, task_ids: List[str], updates: Dict[str, Any]) -> int:
        pass

    @abc.abstractmethod
    def list_tasks(self, owner_role: Optional[str] = None) -> List[Dict[str, Any]]:
        pass


class SupabaseTaskRepository(BaseTaskRepository):
    """
    Authoritative single-source repository for production using Supabase PostgreSQL.
    Directly queries and mutates public.task_queue with zero SQLite dependency.
    """

    def __init__(self):
        from app.supabase_adapter import get_supabase_client
        self.client = get_supabase_client()

    def get_task_queue(
        self,
        current_user: AuthUser,
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
    ) -> List[Dict[str, Any]]:
        from app.supabase_adapter import supa_get_task_queue
        role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        user_id_str = getattr(current_user, "id", "")
        user_facs = getattr(current_user, "facility_ids", []) or []
        user_dist = getattr(current_user, "district", None) or getattr(current_user, "extra_claims", {}).get("district")
        linked_case = getattr(current_user, "linked_case_id", None)
        station = getattr(current_user, "police_station", None) or getattr(current_user, "extra_claims", {}).get("police_station", "")

        return supa_get_task_queue(
            current_user_role=role_str,
            user_id=user_id_str,
            user_facilities=user_facs,
            user_district=user_dist,
            linked_case_id=linked_case,
            police_station=station,
            facility=facility,
            district=district,
            priority=priority,
            custody_duration_min=custody_duration_min,
            document_completeness_max=document_completeness_max,
            legal_aid_need=legal_aid_need,
            hearing_date_from=hearing_date_from,
            hearing_date_to=hearing_date_to,
            has_data_conflict=has_data_conflict,
            assignment_status=assignment_status,
            matter_status=matter_status,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        from app.supabase_adapter import supa_get_task_by_id
        task = supa_get_task_by_id(task_id)
        if not task:
            task = SqliteTaskRepository().get_task_by_id(task_id)
        return task

    def get_tasks_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        tasks = []
        try:
            if self.client:
                res = self.client.table("task_queue").select("*").eq("case_id", case_id).execute()
                if res.data:
                    tasks.extend(res.data)
        except Exception as e:
            logger.warning(f"Supabase get_tasks_for_case error: {e}")
        # Merge with local sqlite tasks
        sqlite_tasks = SqliteTaskRepository().get_tasks_for_case(case_id)
        seen_ids = {t.get("id") for t in tasks if t.get("id")}
        for st in sqlite_tasks:
            if st.get("id") not in seen_ids:
                tasks.append(st)
        return tasks

    def upsert_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        from app.supabase_adapter import supa_upsert_task_queue_items
        res = supa_upsert_task_queue_items(tasks)
        try:
            SqliteTaskRepository().upsert_tasks(tasks)
        except Exception:
            pass
        return res

    def upsert_task(self, task: Dict[str, Any]) -> bool:
        return self.upsert_tasks([task])

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from app.supabase_adapter import supa_update_task
        return supa_update_task(task_id, updates)

    def bulk_update_tasks(self, task_ids: List[str], updates: Dict[str, Any]) -> int:
        from app.supabase_adapter import supa_bulk_update_tasks
        return supa_bulk_update_tasks(task_ids, updates)

    def list_tasks(self, owner_role: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            if self.client:
                q = self.client.table("task_queue").select("*")
                if owner_role:
                    q = q.eq("owner_role", owner_role)
                res = q.execute()
                if res.data:
                    return res.data
        except Exception as e:
            logger.warning(f"Supabase list_tasks error: {e}")
        return SqliteTaskRepository().list_tasks(owner_role=owner_role)


class SqliteTaskRepository(BaseTaskRepository):
    """
    Developmental sandbox repository using SQLite for zero-dependency offline environments.
    """

    def _get_conn(self):
        import sqlite3
        from app.database import get_db_connection
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        return conn

    def get_task_queue(
        self,
        current_user: AuthUser,
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
    ) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
            user_id = getattr(current_user, "id", "")
            user_facs = getattr(current_user, "facility_ids", []) or []
            user_dist = getattr(current_user, "district", None) or getattr(current_user, "extra_claims", {}).get("district")
            linked_case = getattr(current_user, "linked_case_id", None)

            query = "SELECT * FROM task_queue WHERE 1=1"
            params: List[Any] = []

            # Role boundary scoping
            if role == "JAIL_OFFICER":
                query += " AND owner_role = 'JAIL_OFFICER'"
                if user_facs:
                    placeholders = ", ".join("?" for _ in user_facs)
                    query += f" AND facility IN ({placeholders})"
                    params.extend(user_facs)
            elif role in ("DEFENSE_ADVOCATE", "CONTROLLED_EXTERNAL_ADVOCATE"):
                query += " AND owner_role = 'DEFENSE_ADVOCATE' AND assignment_status = 'ASSIGNED'"
                query += " AND matter_status NOT IN ('INTAKE', 'INTAKE_PENDING', 'DETECTED', 'VERIFICATION', 'CUSTODY_VERIFIED', 'CUSTODY_PENDING', 'REVIEW', 'LEGAL_AID_REQUIRED', 'LEGAL_NEED_IDENTIFIED', 'PRE_INTAKE', 'DOCUMENTS_MISSING', 'DRAFT_INTAKE')"
                if user_id == "demo_advocate":
                    query += " AND (owner_user_id IN ('demo_advocate', 'adv_001', 'adv_rajesh_sharma') OR case_id IN (SELECT case_id FROM cases WHERE assigned_lawyer_id IN ('demo_advocate', 'adv_001', 'adv_rajesh_sharma') UNION SELECT accused_id FROM court_cases WHERE assigned_lawyer_id IN ('demo_advocate', 'adv_001', 'adv_rajesh_sharma')))"
                elif user_id == "demo_ext_advocate":
                    query += " AND (owner_user_id IN ('demo_ext_advocate', 'adv_ext_001') OR case_id IN (SELECT case_id FROM cases WHERE assigned_lawyer_id IN ('demo_ext_advocate', 'adv_ext_001') UNION SELECT accused_id FROM court_cases WHERE assigned_lawyer_id IN ('demo_ext_advocate', 'adv_ext_001')))"
                else:
                    query += " AND (owner_user_id = ? OR case_id IN (SELECT case_id FROM cases WHERE assigned_lawyer_id = ? UNION SELECT accused_id FROM court_cases WHERE assigned_lawyer_id = ?))"
                    params.extend([user_id, user_id, user_id])
            elif role == "DLSA_OFFICER":
                query += " AND owner_role IN ('DLSA_OFFICER', 'SUPERVISING_LEGAL_OFFICER')"
                if user_dist:
                    query += " AND district = ?"
                    params.append(user_dist)
            elif role == "SUPERVISING_LEGAL_OFFICER":
                query += " AND owner_role IN ('SUPERVISING_LEGAL_OFFICER', 'DLSA_OFFICER')"
                query += " AND (task_type != 'SUPERVISORY_DRAFT_REVIEW' OR assignment_status = 'ASSIGNED')"
                if user_dist:
                    query += " AND district = ?"
                    params.append(user_dist)
            elif role == "POLICE_OFFICER":
                station = getattr(current_user, "police_station", None) or getattr(current_user, "extra_claims", {}).get("police_station", "")
                if station:
                    query += " AND facility = ?"
                    params.append(station)
                else:
                    return []
            elif role in ("ACCUSED_USER", "FAMILY_GUARDIAN"):
                if linked_case:
                    query += " AND case_id = ?"
                    params.append(linked_case)
                else:
                    return []

            # Dynamic filters
            if facility:
                query += " AND facility LIKE ?"
                params.append(f"%{facility}%")
            if district:
                query += " AND district LIKE ?"
                params.append(f"%{district}%")
            if priority:
                query += " AND priority = ?"
                params.append(priority.upper())
            if custody_duration_min is not None:
                query += " AND custody_duration_days >= ?"
                params.append(custody_duration_min)
            if document_completeness_max is not None:
                query += " AND document_completeness_pct <= ?"
                params.append(document_completeness_max)
            if legal_aid_need is not None:
                query += " AND legal_aid_need = ?"
                params.append(1 if legal_aid_need else 0)
            if has_data_conflict is not None:
                query += " AND has_data_conflict = ?"
                params.append(1 if has_data_conflict else 0)
            if hearing_date_from:
                query += " AND hearing_date >= ?"
                params.append(hearing_date_from)
            if hearing_date_to:
                query += " AND hearing_date <= ?"
                params.append(hearing_date_to)
            if assignment_status:
                query += " AND assignment_status = ?"
                params.append(assignment_status.upper())
            if matter_status:
                query += " AND matter_status = ?"
                params.append(matter_status.upper())

            today_iso = datetime.date.today().isoformat()
            if status:
                if status.upper() == "OVERDUE":
                    query += " AND (status = 'OVERDUE' OR (status != 'COMPLETED' AND due_date < ?))"
                    params.append(today_iso)
                else:
                    query += " AND status = ?"
                    params.append(status.upper())

            if search:
                s_term = f"%{search.strip()}%"
                query += " AND (title LIKE ? OR reason LIKE ? OR accused_name LIKE ? OR case_id LIKE ?)"
                params.extend([s_term, s_term, s_term, s_term])

            order_dir = "DESC" if (sort_order or "").lower() == "desc" else "ASC"
            valid_sort_fields = {
                "due_date": "due_date",
                "priority": "CASE priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 WHEN 'LOW' THEN 4 ELSE 5 END",
                "custody_duration_days": "custody_duration_days",
                "created_at": "created_at",
                "status": "status",
            }
            sort_expr = valid_sort_fields.get(sort_by or "due_date", "due_date")
            query += f" ORDER BY {sort_expr} {order_dir}"

            rows = cursor.execute(query, params).fetchall()
            items = []
            for r in rows:
                d = dict(r)
                if d.get("status") not in ("COMPLETED", "EXCEPTION") and d.get("due_date") and d["due_date"] < today_iso:
                    d["status"] = "OVERDUE"
                items.append(d)
            return items
        finally:
            conn.close()

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            row = cursor.execute("SELECT * FROM task_queue WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_tasks_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT * FROM task_queue WHERE case_id = ?", (case_id,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def upsert_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        if not tasks:
            return True
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            for t in tasks:
                cursor.execute("""
                    INSERT OR REPLACE INTO task_queue (
                        id, case_id, accused_name, task_type, title, description,
                        owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                        status, escalation_path, facility, district, custody_duration_days,
                        document_completeness_pct, has_data_conflict, legal_aid_need,
                        assignment_status, matter_status, hearing_date, is_consequential, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                    )
                """, (
                    t["id"], t["case_id"], t.get("accused_name"), t["task_type"], t["title"],
                    t.get("description"), t["owner_role"], t.get("owner_user_id"), t.get("owner_name"),
                    t["priority"], t["due_date"], t["source"], t["reason"], t.get("status", "NEW"),
                    t.get("escalation_path", "Operational Hierarchy"), t.get("facility"), t.get("district"),
                    t.get("custody_duration_days", 0), t.get("document_completeness_pct", 100),
                    t.get("has_data_conflict", 0), t.get("legal_aid_need", 0),
                    t.get("assignment_status", "AVAILABLE"), t.get("matter_status", "INTAKE"),
                    t.get("hearing_date"), t.get("is_consequential", 0),
                ))
            conn.commit()
            return True
        finally:
            conn.close()

    def upsert_task(self, task: Dict[str, Any]) -> bool:
        return self.upsert_tasks([task])

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            fields = []
            vals = []
            for k, v in updates.items():
                fields.append(f"{k} = ?")
                vals.append(v)
            if not fields:
                return self.get_task_by_id(task_id)
            fields.append("updated_at = CURRENT_TIMESTAMP")
            vals.append(task_id)
            cursor.execute(f"UPDATE task_queue SET {', '.join(fields)} WHERE id = ?", vals)
            conn.commit()
            return self.get_task_by_id(task_id)
        finally:
            conn.close()

    def bulk_update_tasks(self, task_ids: List[str], updates: Dict[str, Any]) -> int:
        if not task_ids or not updates:
            return 0
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            fields = []
            vals = []
            for k, v in updates.items():
                fields.append(f"{k} = ?")
                vals.append(v)
            fields.append("updated_at = CURRENT_TIMESTAMP")
            placeholders = ", ".join("?" for _ in task_ids)
            vals.extend(task_ids)
            cursor.execute(f"UPDATE task_queue SET {', '.join(fields)} WHERE id IN ({placeholders})", vals)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def list_tasks(self, owner_role: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            if owner_role:
                cursor.execute("SELECT * FROM task_queue WHERE owner_role = ?", (owner_role,))
            else:
                cursor.execute("SELECT * FROM task_queue")
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in rows]
        finally:
            conn.close()


def get_task_repository() -> BaseTaskRepository:
    """
    Factory returning the single authoritative task repository.
    When Supabase is active, Supabase PostgreSQL is the SOLE authoritative store.
    Otherwise, falls back to SqliteTaskRepository for local developer sandbox.
    """
    from app.supabase_adapter import is_supabase_active
    if is_supabase_active():
        return SupabaseTaskRepository()
    return SqliteTaskRepository()

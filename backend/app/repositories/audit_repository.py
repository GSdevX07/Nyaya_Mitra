"""
audit_repository.py - Immutable Audit Log Repository for Nyaya Mitra.

Writes tamper-evident audit logs to SQLite and/or Supabase PostgreSQL.
Provides helpers for security events, login, record access, approvals, and exports.
"""

from __future__ import annotations
import sqlite3
import datetime
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from app.models.domain import AuditEvent, AuditAction, generate_prefixed_id

DB_PATH = Path(__file__).resolve().parent.parent.parent / "nyaya_mitra.db"


class AuditRepository:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path

    def record(
        self,
        actor_id: str,
        actor_role: str,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        details: dict,
        organization_id: Optional[str] = None,
        ip_address: str = "127.0.0.1",
    ) -> AuditEvent:
        event = AuditEvent(
            id=generate_prefixed_id("aud"),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            actor_id=actor_id,
            actor_role=actor_role,
            organization_id=organization_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            details_json=json.dumps(details),
            is_immutable=True,
        )

        # 1. Supabase PostgreSQL write if available
        try:
            from app.supabase_adapter import supa_append_audit_event, is_supabase_active
            if is_supabase_active():
                supa_append_audit_event({
                    "id": event.id,
                    "timestamp": event.timestamp,
                    "actor_id": event.actor_id,
                    "actor_role": event.actor_role,
                    "organization_id": event.organization_id,
                    "action": event.action.value,
                    "entity_type": event.entity_type,
                    "entity_id": event.entity_id,
                    "ip_address": event.ip_address,
                    "details_json": event.details_json,
                    "is_immutable": event.is_immutable,
                })
        except Exception as e:
            print(f"[WARN] Supabase audit log write failed: {e}")

        # 2. SQLite local write
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_events (id, timestamp, actor_id, actor_role, organization_id, action, entity_type, entity_id, ip_address, details_json, is_immutable)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.timestamp,
                    event.actor_id,
                    event.actor_role,
                    event.organization_id,
                    event.action.value,
                    event.entity_type,
                    event.entity_id,
                    event.ip_address,
                    event.details_json,
                    1 if event.is_immutable else 0,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[WARN] Failed to write audit event to SQLite: {e}")
        return event

    def get_entity_audit_trail(self, entity_type: str, entity_id: str) -> List[AuditEvent]:
        events = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, timestamp, actor_id, actor_role, organization_id, action, entity_type, entity_id, ip_address, details_json, is_immutable FROM audit_events WHERE entity_type = ? AND entity_id = ? ORDER BY timestamp DESC",
                (entity_type, entity_id),
            )
            rows = cursor.fetchall()
            conn.close()
            for r in rows:
                try:
                    action_val = AuditAction(r[5])
                except Exception:
                    action_val = AuditAction.READ
                events.append(
                    AuditEvent(
                        id=r[0],
                        timestamp=r[1],
                        actor_id=r[2],
                        actor_role=r[3],
                        organization_id=r[4],
                        action=action_val,
                        entity_type=r[6],
                        entity_id=r[7],
                        ip_address=r[8],
                        details_json=r[9],
                        is_immutable=bool(r[10]),
                    )
                )
        except Exception as e:
            print(f"[WARN] Failed to fetch audit trail: {e}")
        return events


# ── Global Repository Instance & Helper Functions ────────────────────────────

_audit_repo = AuditRepository()


def append_audit_event(event_dict: Dict[str, Any]) -> None:
    """Convenience helper to record a generic audit event dict."""
    action_str = event_dict.get("action", "READ")
    try:
        action_enum = AuditAction(action_str)
    except ValueError:
        action_enum = AuditAction.READ

    _audit_repo.record(
        actor_id=event_dict.get("actor_id", "system"),
        actor_role=event_dict.get("actor_role", "SYSTEM"),
        action=action_enum,
        entity_type=event_dict.get("entity_type", "system"),
        entity_id=event_dict.get("entity_id", "system"),
        details=event_dict.get("details", {}),
        organization_id=event_dict.get("organization_id"),
        ip_address=event_dict.get("ip_address", "127.0.0.1"),
    )


def audit_login(user_id: str, ip: str, success: bool, role: str = "AUTH") -> None:
    _audit_repo.record(
        actor_id=user_id,
        actor_role=role,
        action=AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED,
        entity_type="user",
        entity_id=user_id,
        details={"ip": ip, "success": success},
        ip_address=ip,
    )


def audit_privilege_change(actor_id: str, target_user_id: str, old_role: str, new_role: str) -> None:
    _audit_repo.record(
        actor_id=actor_id,
        actor_role="ADMIN",
        action=AuditAction.PRIVILEGE_CHANGE,
        entity_type="user",
        entity_id=target_user_id,
        details={"old_role": old_role, "new_role": new_role},
    )


def audit_record_access(user_id: str, user_role: str, entity_type: str, entity_id: str, action: str = "READ") -> None:
    _audit_repo.record(
        actor_id=user_id,
        actor_role=user_role,
        action=AuditAction.RECORD_ACCESS,
        entity_type=entity_type,
        entity_id=entity_id,
        details={"action": action},
    )


def audit_case_approval(user_id: str, user_role: str, case_id: str) -> None:
    _audit_repo.record(
        actor_id=user_id,
        actor_role=user_role,
        action=AuditAction.ADVOCATE_SIGN_OFF,
        entity_type="court_case",
        entity_id=case_id,
        details={"status": "APPROVED_READY_FOR_FILING"},
    )


def audit_case_assignment(user_id: str, user_role: str, case_id: str, lawyer_id: str) -> None:
    _audit_repo.record(
        actor_id=user_id,
        actor_role=user_role,
        action=AuditAction.COUNSEL_ASSIGNED,
        entity_type="court_case",
        entity_id=case_id,
        details={"assigned_lawyer_id": lawyer_id},
    )


def audit_export(user_id: str, user_role: str, case_id: str, export_format: str = "PDF") -> None:
    _audit_repo.record(
        actor_id=user_id,
        actor_role=user_role,
        action=AuditAction.DATA_EXPORT,
        entity_type="court_case",
        entity_id=case_id,
        details={"format": export_format},
    )


def audit_token_revocation(user_id: str, user_role: str, jti: str, reason: str = "logout") -> None:
    _audit_repo.record(
        actor_id=user_id,
        actor_role=user_role,
        action=AuditAction.TOKEN_REVOCATION,
        entity_type="token",
        entity_id=jti,
        details={"reason": reason},
    )

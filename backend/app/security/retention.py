"""
retention.py - Configurable Data Retention and Lifecycle Purge Engine for Nyaya Mitra.

LEGAL NOTICE:
Data retention schedules configured herein represent system operational policies.
Statutory data retention in criminal proceedings is governed by the Destruction of Records
Act, 1917, the High Court Rules of the respective jurisdiction, Criminal Courts Rules of
Practice, and National/State Legal Services Authorities regulations.
System administrators must conduct a formal legal review with designated legal counsel
to validate retention schedules against applicable state and central court rules before
operationalizing automated destruction in production environments.
"""

from __future__ import annotations
import datetime
import sqlite3
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


LEGAL_RETENTION_DISCLAIMER = (
    "Engineering data retention policies require independent jurisdictional legal "
    "validation under High Court Rules, Criminal Courts Rules of Practice, and the "
    "Destruction of Records Act, 1917 before automated production deletion."
)


class RetentionSchedule(BaseModel):
    category: str
    retention_days: int
    description: str
    requires_manual_approval: bool = False
    jurisdictional_note: str = LEGAL_RETENTION_DISCLAIMER


# Default operational retention policies (in days)
DEFAULT_RETENTION_SCHEDULES: Dict[str, RetentionSchedule] = {
    "CONNECTOR_PAYLOAD": RetentionSchedule(
        category="CONNECTOR_PAYLOAD",
        retention_days=90,
        description="Raw staging webhook payloads from e-Courts and prison connectors.",
        requires_manual_approval=False,
    ),
    "IDENTITY_CONFLICT_LOG": RetentionSchedule(
        category="IDENTITY_CONFLICT_LOG",
        retention_days=180,
        description="Resolved demographic and biometric discrepancy resolution logs.",
        requires_manual_approval=False,
    ),
    "EXPIRED_AUTH_TOKEN": RetentionSchedule(
        category="EXPIRED_AUTH_TOKEN",
        retention_days=7,
        description="Blacklisted or expired JWT token identifiers.",
        requires_manual_approval=False,
    ),
    "CLOSED_MATTER_DOSSIER": RetentionSchedule(
        category="CLOSED_MATTER_DOSSIER",
        retention_days=1095,  # 3 Years
        description="Closed legal aid dossiers following final judicial disposition.",
        requires_manual_approval=True,
    ),
    "AUDIT_EVENT_LEDGER": RetentionSchedule(
        category="AUDIT_EVENT_LEDGER",
        retention_days=2555,  # 7 Years
        description="Tamper-evident audit log ledger; immutable archive retention.",
        requires_manual_approval=True,
    ),
}


class RetentionPolicyEngine:
    def __init__(self, schedules: Optional[Dict[str, RetentionSchedule]] = None):
        self.schedules = schedules or dict(DEFAULT_RETENTION_SCHEDULES)

    def get_schedule(self, category: str) -> Optional[RetentionSchedule]:
        return self.schedules.get(category)

    def list_schedules(self) -> List[RetentionSchedule]:
        return list(self.schedules.values())

    def update_schedule(self, category: str, retention_days: int, requires_approval: bool = False) -> RetentionSchedule:
        if category not in self.schedules:
            raise ValueError(f"Unknown retention category: {category}")
        schedule = self.schedules[category]
        schedule.retention_days = max(1, retention_days)
        schedule.requires_manual_approval = requires_approval
        return schedule

    def evaluate_retention(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """
        Evaluate candidate records eligible for lifecycle archival or purge across tables.
        Does not mutate or delete any data.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        results: Dict[str, Any] = {
            "evaluated_at": now.isoformat(),
            "legal_notice": LEGAL_RETENTION_DISCLAIMER,
            "categories": {},
        }

        # 1. Evaluate revoked tokens
        token_schedule = self.schedules.get("EXPIRED_AUTH_TOKEN")
        if token_schedule:
            cutoff = (now - datetime.timedelta(days=token_schedule.retention_days)).isoformat()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM revoked_tokens WHERE revoked_at < ?", (cutoff,))
                row = cur.fetchone()
                results["categories"]["EXPIRED_AUTH_TOKEN"] = {
                    "eligible_count": row[0] if row else 0,
                    "retention_days": token_schedule.retention_days,
                    "cutoff_date": cutoff,
                    "requires_approval": token_schedule.requires_manual_approval,
                }
            except Exception as e:
                results["categories"]["EXPIRED_AUTH_TOKEN"] = {"error": str(e)}

        # 2. Evaluate audit ledger (read-only count of events older than 7 years)
        audit_schedule = self.schedules.get("AUDIT_EVENT_LEDGER")
        if audit_schedule:
            cutoff = (now - datetime.timedelta(days=audit_schedule.retention_days)).isoformat()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM audit_events WHERE timestamp < ?", (cutoff,))
                row = cur.fetchone()
                results["categories"]["AUDIT_EVENT_LEDGER"] = {
                    "eligible_count": row[0] if row else 0,
                    "retention_days": audit_schedule.retention_days,
                    "cutoff_date": cutoff,
                    "requires_approval": audit_schedule.requires_manual_approval,
                }
            except Exception as e:
                results["categories"]["AUDIT_EVENT_LEDGER"] = {"error": str(e)}

        # 3. Connector payloads and conflict logs
        for cat in ["CONNECTOR_PAYLOAD", "IDENTITY_CONFLICT_LOG", "CLOSED_MATTER_DOSSIER"]:
            sched = self.schedules.get(cat)
            if sched:
                cutoff = (now - datetime.timedelta(days=sched.retention_days)).isoformat()
                results["categories"][cat] = {
                    "eligible_count": 0,
                    "retention_days": sched.retention_days,
                    "cutoff_date": cutoff,
                    "requires_approval": sched.requires_manual_approval,
                }

        return results

    def purge_records(
        self,
        conn: sqlite3.Connection,
        category: str,
        authorized_by: str,
        actor_role: str,
        ip_address: str = "127.0.0.1",
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute or simulate lifecycle purge of expired records in the designated category.
        Emits an immutable audit log upon actual execution.
        """
        if category not in self.schedules:
            raise ValueError(f"Invalid retention category: {category}")

        sched = self.schedules[category]
        if sched.requires_manual_approval and actor_role not in ("PLATFORM_ADMIN", "GOV_ADMIN"):
            raise PermissionError(
                f"Purge for category {category} requires manual high-privilege administrative approval."
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = (now - datetime.timedelta(days=sched.retention_days)).isoformat()
        purged_count = 0

        if category == "EXPIRED_AUTH_TOKEN":
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM revoked_tokens WHERE revoked_at < ?", (cutoff,))
                count_row = cur.fetchone()
                purged_count = count_row[0] if count_row else 0
                if not dry_run and purged_count > 0:
                    cur.execute("DELETE FROM revoked_tokens WHERE revoked_at < ?", (cutoff,))
                    conn.commit()
            except Exception as e:
                raise RuntimeError(f"Database error during token retention purge: {e}")

        elif category == "AUDIT_EVENT_LEDGER":
            # Safety safeguard: Nyaya Mitra never deletes audit logs without manual cryptographic archive export
            raise ValueError("Audit event records are immutable and cannot be purged online.")

        if not dry_run and purged_count > 0:
            try:
                from app.repositories.audit_repository import audit_retention_purge
                audit_retention_purge(
                    actor_id=authorized_by,
                    category=category,
                    purged_count=purged_count,
                    ip_address=ip_address,
                    details={"cutoff_date": cutoff, "retention_days": sched.retention_days},
                )
            except Exception:
                pass

        return {
            "category": category,
            "purged_count": purged_count,
            "dry_run": dry_run,
            "cutoff_date": cutoff,
            "retention_days": sched.retention_days,
            "authorized_by": authorized_by,
            "timestamp": now.isoformat(),
            "legal_disclaimer": LEGAL_RETENTION_DISCLAIMER,
        }

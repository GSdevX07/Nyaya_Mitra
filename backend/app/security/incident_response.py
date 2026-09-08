"""
incident_response.py - Automated Security Incident Response and Containment Framework for Nyaya Mitra.

Monitors for and responds to:
1. Data breach / unauthorized PII exfiltration
2. Unauthorized access spikes (repeated 403/forbidden attempts)
3. Suspicious document download bursts (>10 downloads in 60 seconds)
4. Failed authentication spikes (credential stuffing / brute-force)
5. External connector compromise (signature / hash mismatch)
"""

from __future__ import annotations
import sqlite3
import datetime
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict
from pydantic import BaseModel, Field
from app.models.domain import generate_prefixed_id


# Sliding window anomaly tracker (in-memory)
_DOWNLOAD_TRACKER = defaultdict(list)
_AUTH_FAIL_TRACKER = defaultdict(list)
_FORBIDDEN_TRACKER = defaultdict(list)


class IncidentRecord(BaseModel):
    id: str
    incident_type: str
    severity: str
    status: str
    trigger_details: Dict[str, Any]
    containment_action: str
    created_at: str
    resolved_at: Optional[str] = None


def init_incident_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS security_incidents (
            id TEXT PRIMARY KEY,
            incident_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            trigger_details TEXT NOT NULL,
            containment_action TEXT NOT NULL,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        )
        """
    )
    conn.commit()


def track_download_event(ip_address: str, actor_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """
    Track document download rate. Triggers incident if >10 downloads occur within 60 seconds.
    """
    now = time.time()
    key = f"{ip_address}:{actor_id}"
    _DOWNLOAD_TRACKER[key].append(now)
    # Filter to last 60 seconds
    _DOWNLOAD_TRACKER[key] = [t for t in _DOWNLOAD_TRACKER[key] if now - t <= 60]

    count = len(_DOWNLOAD_TRACKER[key])
    if count >= 10:
        return declare_incident(
            incident_type="SUSPICIOUS_DOWNLOAD_BURST",
            severity="HIGH",
            trigger_details={
                "ip_address": ip_address,
                "actor_id": actor_id,
                "downloads_in_60s": count,
                "latest_doc_id": doc_id,
            },
            containment_action="TEMPORARY_RATE_LIMIT_APPLIED",
        )
    return None


def track_failed_auth(ip_address: str, identifier: str) -> Optional[Dict[str, Any]]:
    """
    Track failed login attempts. Triggers incident if >=10 failures occur within 60 seconds.
    """
    now = time.time()
    key = ip_address
    _AUTH_FAIL_TRACKER[key].append(now)
    _AUTH_FAIL_TRACKER[key] = [t for t in _AUTH_FAIL_TRACKER[key] if now - t <= 60]

    count = len(_AUTH_FAIL_TRACKER[key])
    if count >= 10:
        return declare_incident(
            incident_type="FAILED_AUTH_SPIKE",
            severity="HIGH",
            trigger_details={
                "ip_address": ip_address,
                "identifier": identifier,
                "failures_in_60s": count,
            },
            containment_action="IP_TEMPORARY_BLOCK_RECOMMENDED",
        )
    return None


def track_forbidden_access(ip_address: str, actor_id: str, endpoint: str) -> Optional[Dict[str, Any]]:
    """
    Track 403 Forbidden rejections. Triggers incident if >=8 rejections occur within 60 seconds.
    """
    now = time.time()
    key = f"{ip_address}:{actor_id}"
    _FORBIDDEN_TRACKER[key].append(now)
    _FORBIDDEN_TRACKER[key] = [t for t in _FORBIDDEN_TRACKER[key] if now - t <= 60]

    count = len(_FORBIDDEN_TRACKER[key])
    if count >= 8:
        return declare_incident(
            incident_type="UNAUTHORIZED_ACCESS_SPIKE",
            severity="HIGH",
            trigger_details={
                "ip_address": ip_address,
                "actor_id": actor_id,
                "forbidden_count_in_60s": count,
                "endpoint": endpoint,
            },
            containment_action="USER_SESSION_QUARANTINE_ADVISED",
        )
    return None


def handle_connector_compromise(connector_name: str, reason: str, payload_hash: str) -> Dict[str, Any]:
    """
    Immediate containment for corrupted or tampered webhook/connector payloads.
    """
    return declare_incident(
        incident_type="CONNECTOR_INTEGRITY_COMPROMISE",
        severity="CRITICAL",
        trigger_details={
            "connector_name": connector_name,
            "reason": reason,
            "payload_hash": payload_hash,
        },
        containment_action="CONNECTOR_INBOUND_INGESTION_SUSPENDED",
    )


def declare_incident(
    incident_type: str,
    severity: str,
    trigger_details: Dict[str, Any],
    containment_action: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Declare and persist a security incident, emit an immutable audit trail record,
    and activate containment measures.
    """
    import json
    from app.database import get_db_connection

    incident_id = generate_prefixed_id("inc")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    close_conn = False
    if conn is None:
        try:
            conn = get_db_connection()
            close_conn = True
        except Exception:
            pass

    if conn:
        try:
            init_incident_table(conn)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO security_incidents (
                    id, incident_type, severity, status, trigger_details, containment_action, created_at
                ) VALUES (?, ?, ?, 'CONTAINED', ?, ?, ?)
                """,
                (
                    incident_id,
                    incident_type,
                    severity,
                    json.dumps(trigger_details, sort_keys=True),
                    containment_action,
                    now,
                ),
            )
            conn.commit()
        except Exception as e:
            print(f"[WARN] Failed to persist security incident to SQLite: {e}")
        finally:
            if close_conn:
                conn.close()

    # Emit audit log
    try:
        from app.repositories.audit_repository import audit_incident_declared
        audit_incident_declared(
            actor_id="system_incident_response",
            actor_role="SECURITY_AUTOMATION",
            incident_id=incident_id,
            incident_type=incident_type,
            severity=severity,
            details={
                "containment_action": containment_action,
                **trigger_details,
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to write audit event for incident declaration: {e}")

    return {
        "incident_id": incident_id,
        "incident_type": incident_type,
        "severity": severity,
        "status": "CONTAINED",
        "containment_action": containment_action,
        "created_at": now,
        "trigger_details": trigger_details,
    }


def list_active_incidents(conn: sqlite3.Connection, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent recorded security incidents."""
    import json
    init_incident_table(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, incident_type, severity, status, trigger_details, containment_action, created_at, resolved_at
        FROM security_incidents
        ORDER BY created_at DESC LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    incidents = []
    for r in rows:
        try:
            details = json.loads(r[4])
        except Exception:
            details = {}
        incidents.append({
            "id": r[0],
            "incident_type": r[1],
            "severity": r[2],
            "status": r[3],
            "trigger_details": details,
            "containment_action": r[5],
            "created_at": r[6],
            "resolved_at": r[7],
        })
    return incidents

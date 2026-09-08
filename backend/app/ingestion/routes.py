"""
ingestion/routes.py — REST API Endpoints for External Data Ingestion, Connectors & Governance.

Endpoints:
  GET  /ingestion/connectors                — Telemetry & health of all source adapters
  GET  /ingestion/connectors/{id}/health    — Granular health telemetry for a single connector
  POST /ingestion/connectors/{id}/sync      — Trigger immediate sync for polling/simulated feeds
  POST /ingestion/upload                   — Structured CSV / spreadsheet import
  POST /ingestion/manual-entry             — Controlled manual intake desk form
  GET  /ingestion/dashboard                — Overview metrics, active/stale feeds, error counts
  GET  /ingestion/conflicts                — Field conflicts queue (filtered by status)
  GET  /ingestion/conflicts/{id}           — Single conflict inspection
  POST /ingestion/conflicts/{id}/resolve   — Human review gateway (Keep Canonical / Adopt / Override)
  GET  /ingestion/audit-logs               — Connector outbound audit logs
  GET  /ingestion/identity-merges          — Uncertain identity matches awaiting confirmation
  POST /ingestion/identity-merges/{id}/res — Confirm or separate identity candidate
"""

from __future__ import annotations
import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, Query, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, require_role
from app.auth.roles import Role
from app.auth.user_store import AuthUser
from app.ingestion.models import (
    ConnectorConfig, IngestionDashboardTelemetry, FieldConflict, ConflictStatus,
    IdentityMatchCandidate, ResolutionStatus, ConflictResolutionRequest,
    ConnectorAuditLogEntry
)
from app.ingestion.connectors.spreadsheet_connector import SpreadsheetConnector
from app.ingestion.connectors.manual_entry_connector import ManualEntryConnector
from app.ingestion.connectors.ecourts_connector import ECourtsConnector
from app.ingestion.connectors.eprisons_connector import EPrisonsConnector
from app.ingestion.connectors.cctns_connector import CCTNSConnector
from app.ingestion.connectors.gov_prosecution_connector import GovProsecutionConnector
from app.ingestion.connectors.dlsa_legalaid_connector import DLSALegalAidConnector
from app.ingestion.pipeline import (
    get_ingestion_pipeline, get_pending_conflicts, get_pending_identity_merges,
    resolve_field_conflict, _PENDING_IDENTITY_MERGES, _load_conflicts_from_db
)
from app.database import get_db_connection
from app.auth.config import DEMO_MODE


ingestion_router = APIRouter(tags=["Data Ingestion & Governance"])

# ── Singleton Registry of Active Connectors ───────────────────────────────────

_ecourts_conn = ECourtsConnector()
_eprisons_conn = EPrisonsConnector()
_cctns_conn = CCTNSConnector()
_prosecution_conn = GovProsecutionConnector()
_dlsa_conn = DLSALegalAidConnector()
_spreadsheet_conn = SpreadsheetConnector()
_manual_conn = ManualEntryConnector()

# Registry supporting both primary IDs and legacy simulated aliases
_PRIMARY_CONNECTORS = [
    _ecourts_conn,
    _eprisons_conn,
    _cctns_conn,
    _prosecution_conn,
    _dlsa_conn,
    _spreadsheet_conn,
    _manual_conn,
]

_REGISTRY = {c.config.id: c for c in _PRIMARY_CONNECTORS}

# Legacy alias mappings for backwards test compatibility
_REGISTRY["conn_simulated_ecourts"] = _ecourts_conn
_REGISTRY["conn_simulated_eprisons"] = _eprisons_conn
_REGISTRY["conn_simulated_cctns"] = _cctns_conn


# ── Request Payloads ──────────────────────────────────────────────────────────

class IdentityMergeRequest(BaseModel):
    confirm_merge: bool
    notes: Optional[str] = "Reviewed official dossier match"


# ── Routes ────────────────────────────────────────────────────────────────────

@ingestion_router.get("/connectors", response_model=List[ConnectorConfig])
def list_connectors(
    current_user: AuthUser = Depends(require_role(Role.PLATFORM_ADMIN))
):
    """List all registered external institutional connectors and their live sync health."""
    return [c.config for c in _PRIMARY_CONNECTORS]


@ingestion_router.get("/connectors/{connector_id}/health")
def get_connector_health(
    connector_id: str,
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.DLSA_OFFICER,
        Role.SUPERVISING_LEGAL_OFFICER, Role.READ_ONLY_AUDITOR
    ))
):
    """Retrieve detailed operational health telemetry for a single connector."""
    conn = _REGISTRY.get(connector_id)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")

    c = conn.config
    return {
        "id": c.id,
        "name": c.name,
        "display_name": c.display_name,
        "status": c.operational_status.value,
        "sync_status": c.sync_status.value,
        "is_sandbox": c.is_simulated,
        "last_sync": c.last_successful_sync,
        "next_sync": c.next_sync_at,
        "latency_ms": c.latency_ms,
        "error_rate_pct": c.error_rate_pct,
        "records_processed": c.records_processed,
        "records_rejected": c.records_rejected,
        "records_received": c.records_received,
        "credential_status": c.credential_status.value,
        "credential_expiry": c.credential_expiry,
        "masked_credential": c.masked_credential,
        "rate_limit_per_minute": c.rate_limit_per_minute,
    }


@ingestion_router.get("/dashboard", response_model=IngestionDashboardTelemetry)
def get_ingestion_dashboard(
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.DLSA_OFFICER,
        Role.SUPERVISING_LEGAL_OFFICER, Role.READ_ONLY_AUDITOR
    ))
):
    """Retrieve operational telemetry across all ingestion pipelines."""
    connectors = [c.config for c in _PRIMARY_CONNECTORS]
    total_received = sum(c.records_received for c in connectors)
    total_failures = sum(c.validation_failures for c in connectors)
    pending_conflicts = len(get_pending_conflicts())
    pending_merges = len(get_pending_identity_merges())

    return IngestionDashboardTelemetry(
        connectors=connectors,
        total_records_ingested=total_received,
        validation_failures_total=total_failures,
        conflicts_awaiting_review=pending_conflicts,
        identity_merges_pending=pending_merges,
        active_feeds_count=len([c for c in connectors if c.sync_status.value == "HEALTHY"]),
        stale_feeds_count=len([c for c in connectors if c.sync_status.value == "STALE"]),
        last_sync_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        demo_mode_active=DEMO_MODE,
    )


@ingestion_router.post("/connectors/{connector_id}/sync")
def trigger_connector_sync(
    connector_id: str,
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.SUPERVISING_LEGAL_OFFICER
    ))
):
    """Trigger manual or simulated sync on the requested connector."""
    conn = _REGISTRY.get(connector_id)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")

    pipeline = get_ingestion_pipeline()
    records = []

    if hasattr(conn, "fetch_records"):
        records = conn.fetch_records()
    elif hasattr(conn, "fetch_simulated_feed"):
        records = conn.fetch_simulated_feed()
    else:
        raise HTTPException(
            status_code=400,
            detail="Immediate polling trigger is only applicable to automated / simulated feeds.",
        )

    batch = pipeline.ingest_record_batch(conn, records)

    return {
        "status": "success",
        "connector_id": connector_id,
        "batch_id": batch.id,
        "records_ingested": batch.total_records,
        "valid_records": batch.valid_records,
        "conflicts_detected": batch.conflicts_detected,
        "latency_ms": conn.config.latency_ms,
        "next_sync_at": conn.config.next_sync_at,
    }


@ingestion_router.post("/upload")
async def upload_spreadsheet(
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(require_role(Role.PLATFORM_ADMIN, Role.GOV_ADMIN))
):
    """Upload and parse a CSV / spreadsheet file of undertrial records."""
    if not file.filename or not (file.filename.endswith(".csv") or file.filename.endswith(".txt")):
        raise HTTPException(status_code=415, detail="Only structured CSV files are supported.")

    content_bytes = await file.read()
    try:
        csv_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        csv_text = content_bytes.decode("latin-1")

    rows = _spreadsheet_conn.parse_csv_content(csv_text)
    if not rows:
        raise HTTPException(status_code=422, detail="No readable records found in the uploaded file.")

    pipeline = get_ingestion_pipeline()
    batch = pipeline.ingest_record_batch(_spreadsheet_conn, rows)

    return {
        "status": "success",
        "batch_id": batch.id,
        "total_records": batch.total_records,
        "valid_records": batch.valid_records,
        "invalid_records": batch.invalid_records,
        "conflicts_detected": batch.conflicts_detected,
        "filename": file.filename,
    }


@ingestion_router.post("/manual-entry")
def submit_manual_entry(
    payload: Dict[str, Any] = Body(...),
    current_user: AuthUser = Depends(require_role(Role.PLATFORM_ADMIN, Role.GOV_ADMIN))
):
    """Controlled manual intake desk endpoint."""
    pipeline = get_ingestion_pipeline()
    payload["officer_id"] = current_user.id
    batch = pipeline.ingest_record_batch(_manual_conn, [payload])

    if batch.invalid_records > 0:
        raise HTTPException(
            status_code=422,
            detail="Manual intake validation failed. Check required fields and age constraints.",
        )

    return {
        "status": "success",
        "batch_id": batch.id,
        "message": f"Accused record for '{payload.get('full_name')}' ingested successfully.",
    }


@ingestion_router.get("/conflicts", response_model=List[FieldConflict])
def list_conflicts(
    status_filter: Optional[str] = Query("PENDING_REVIEW", alias="status"),
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.DLSA_OFFICER,
        Role.SUPERVISING_LEGAL_OFFICER, Role.READ_ONLY_AUDITOR
    ))
):
    """Retrieve field-level conflicts awaiting human resolution or historical decisions."""
    all_conflicts = list(_load_conflicts_from_db().values())
    if not all_conflicts:
        all_conflicts = get_pending_conflicts()

    if status_filter and status_filter.upper() != "ALL":
        target = status_filter.upper()
        return [c for c in all_conflicts if c.status.value == target]
    return all_conflicts


@ingestion_router.get("/conflicts/{conflict_id}", response_model=FieldConflict)
def get_conflict_detail(
    conflict_id: str,
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.DLSA_OFFICER,
        Role.SUPERVISING_LEGAL_OFFICER, Role.READ_ONLY_AUDITOR
    ))
):
    """Retrieve details for a single field conflict."""
    db_map = _load_conflicts_from_db()
    conf = db_map.get(conflict_id)
    if not conf:
        raise HTTPException(status_code=404, detail=f"Conflict '{conflict_id}' not found.")
    return conf


@ingestion_router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict_item(
    conflict_id: str,
    body: ConflictResolutionRequest,
    current_user: AuthUser = Depends(require_role(
        Role.SUPERVISING_LEGAL_OFFICER, Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.DLSA_OFFICER
    ))
):
    """Human review sign-off on a field-level conflict (Keep Canonical, Adopt Incoming, or Override)."""
    conf = resolve_field_conflict(
        conflict_id=conflict_id,
        resolution=body.resolution,
        officer_id=current_user.id,
        notes=body.notes or "Resolved during legal review session",
        override_value=body.override_value,
    )
    if not conf:
        raise HTTPException(status_code=404, detail=f"Conflict '{conflict_id}' not found.")

    return {
        "status": "success",
        "conflict_id": conflict_id,
        "resolution": conf.status.value,
        "resolved_by": current_user.id,
        "resolved_at": conf.resolved_at,
        "notes": conf.resolution_notes,
    }


@ingestion_router.get("/audit-logs", response_model=List[ConnectorAuditLogEntry])
def list_connector_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.READ_ONLY_AUDITOR, Role.GOV_ADMIN
    ))
):
    """Retrieve immutable outbound institutional connector audit logs."""
    logs = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM connector_audit_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        for r in rows:
            d = dict(r)
            logs.append(ConnectorAuditLogEntry(
                id=d["id"],
                connector_id=d["connector_id"],
                request_method=d["request_method"],
                endpoint_url=d["endpoint_url"],
                request_headers_masked=d.get("request_headers_masked"),
                request_hash=d.get("request_hash"),
                response_status=int(d.get("response_status") or 200),
                latency_ms=float(d.get("latency_ms") or 0.0),
                idempotency_key=d.get("idempotency_key"),
                attempt_number=int(d.get("attempt_number") or 1),
                error_message=d.get("error_message"),
                created_at=d.get("created_at") or datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ))
        conn.close()
    except Exception:
        pass
    return logs


@ingestion_router.get("/identity-merges", response_model=List[IdentityMatchCandidate])
def list_identity_merges(
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.DLSA_OFFICER,
        Role.SUPERVISING_LEGAL_OFFICER, Role.READ_ONLY_AUDITOR
    ))
):
    """Retrieve probabilistic identity merge candidates requiring review."""
    return get_pending_identity_merges()


@ingestion_router.post("/identity-merges/{merge_id}/resolve")
def resolve_identity_merge_candidate(
    merge_id: str,
    body: IdentityMergeRequest,
    current_user: AuthUser = Depends(require_role(
        Role.SUPERVISING_LEGAL_OFFICER, Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.DLSA_OFFICER
    ))
):
    """Confirm or reject uncertain identity merge candidate."""
    cand = _PENDING_IDENTITY_MERGES.get(merge_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Identity merge candidate '{merge_id}' not found.")

    cand.status = ResolutionStatus.MANUALLY_MERGED if body.confirm_merge else ResolutionStatus.CONFIRMED_SEPARATE
    cand.resolved_by = current_user.id
    cand.resolved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return {
        "status": "success",
        "merge_id": merge_id,
        "resolution": cand.status.value,
        "resolved_by": current_user.id,
    }

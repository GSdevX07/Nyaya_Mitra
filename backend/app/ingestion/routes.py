"""
ingestion/routes.py — REST API Endpoints for Data Ingestion, Connectors & Governance.

Endpoints:
  GET  /ingestion/connectors                — Telemetry & health of all source adapters
  POST /ingestion/connectors/{id}/sync      — Trigger immediate sync for polling/simulated feeds
  POST /ingestion/upload                   — Structured CSV / spreadsheet import
  POST /ingestion/manual-entry             — Controlled manual intake desk form
  GET  /ingestion/dashboard                — Overview metrics, active/stale feeds, error counts
  GET  /ingestion/conflicts                — Pending field conflicts queue
  POST /ingestion/conflicts/{id}/resolve   — Human review gateway for field discrepancies
  GET  /ingestion/identity-merges          — Uncertain identity matches awaiting confirmation
  POST /ingestion/identity-merges/{id}/res — Confirm or separate identity candidate
"""

from __future__ import annotations
import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, require_role
from app.auth.roles import Role
from app.auth.user_store import AuthUser
from app.ingestion.models import (
    ConnectorConfig, IngestionDashboardTelemetry, FieldConflict, ConflictStatus,
    IdentityMatchCandidate, ResolutionStatus
)
from app.ingestion.connectors.spreadsheet_connector import SpreadsheetConnector
from app.ingestion.connectors.manual_entry_connector import ManualEntryConnector
from app.ingestion.connectors.simulated_eprisons import SimulatedEPrisonsConnector
from app.ingestion.connectors.simulated_ecourts import SimulatedECourtsConnector
from app.ingestion.connectors.simulated_cctns import SimulatedCCTNSConnector
from app.ingestion.pipeline import (
    get_ingestion_pipeline, get_pending_conflicts, get_pending_identity_merges,
    resolve_field_conflict, _PENDING_IDENTITY_MERGES
)
from app.auth.config import DEMO_MODE


ingestion_router = APIRouter(tags=["Data Ingestion & Governance"])

# ── Singleton Registry of Active Connectors ───────────────────────────────────

_spreadsheet_conn = SpreadsheetConnector()
_manual_conn = ManualEntryConnector()
_eprisons_conn = SimulatedEPrisonsConnector()
_ecourts_conn = SimulatedECourtsConnector()
_cctns_conn = SimulatedCCTNSConnector()

_REGISTRY = {
    _spreadsheet_conn.config.id: _spreadsheet_conn,
    _manual_conn.config.id: _manual_conn,
    _eprisons_conn.config.id: _eprisons_conn,
    _ecourts_conn.config.id: _ecourts_conn,
    _cctns_conn.config.id: _cctns_conn,
}


# ── Request / Response Payloads ───────────────────────────────────────────────

class ConflictResolutionRequest(BaseModel):
    resolution: ConflictStatus
    notes: Optional[str] = "Resolved during legal review session"


class IdentityMergeRequest(BaseModel):
    confirm_merge: bool
    notes: Optional[str] = "Reviewed official dossier match"


# ── Routes ────────────────────────────────────────────────────────────────────

@ingestion_router.get("/connectors", response_model=List[ConnectorConfig])
def list_connectors(
    current_user: AuthUser = Depends(require_role(Role.PLATFORM_ADMIN))
):
    """List all registered external connectors and their live sync status."""
    return [c.config for c in _REGISTRY.values()]


@ingestion_router.get("/dashboard", response_model=IngestionDashboardTelemetry)
def get_ingestion_dashboard(
    current_user: AuthUser = Depends(require_role(Role.PLATFORM_ADMIN))
):
    """Retrieve operational telemetry across all ingestion pipelines."""
    connectors = [c.config for c in _REGISTRY.values()]
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
    current_user: AuthUser = Depends(require_role(Role.PLATFORM_ADMIN))
):
    """Trigger manual or simulated sync on the requested connector."""
    conn = _REGISTRY.get(connector_id)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")

    pipeline = get_ingestion_pipeline()
    records = []

    if isinstance(conn, SimulatedEPrisonsConnector):
        records = conn.fetch_simulated_feed()
    elif isinstance(conn, SimulatedECourtsConnector):
        records = conn.fetch_simulated_feed()
    elif isinstance(conn, SimulatedCCTNSConnector):
        records = [
            {
                "fir_number": f"FIR-2025-CCTNS-{datetime.datetime.now().strftime('%M%S')}",
                "accused_name": "Rakesh Sharma",
                "police_station": "Kotwali PS",
                "arrest_date": datetime.date.today().isoformat(),
                "offense_sections": ["BNS 303(2)"],
                "age": 29,
            }
        ]
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
    }


@ingestion_router.post("/upload")
async def upload_spreadsheet(
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(require_role(Role.PLATFORM_ADMIN))
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
    current_user: AuthUser = Depends(require_role(Role.PLATFORM_ADMIN))
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
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.DLSA_OFFICER,
        Role.SUPERVISING_LEGAL_OFFICER, Role.READ_ONLY_AUDITOR
    ))
):
    """Retrieve all pending field-level conflicts awaiting human resolution."""
    return get_pending_conflicts()


@ingestion_router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict_item(
    conflict_id: str,
    body: ConflictResolutionRequest,
    current_user: AuthUser = Depends(require_role(
        Role.SUPERVISING_LEGAL_OFFICER, Role.PLATFORM_ADMIN, Role.GOV_ADMIN
    ))
):
    """Human review sign-off on a field-level conflict."""
    conf = resolve_field_conflict(
        conflict_id=conflict_id,
        resolution=body.resolution,
        officer_id=current_user.id,
        notes=body.notes or "",
    )
    if not conf:
        raise HTTPException(status_code=404, detail=f"Conflict '{conflict_id}' not found.")

    return {
        "status": "success",
        "conflict_id": conflict_id,
        "resolution": conf.status.value,
        "resolved_by": current_user.id,
        "resolved_at": conf.resolved_at,
    }


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
        Role.SUPERVISING_LEGAL_OFFICER, Role.PLATFORM_ADMIN, Role.GOV_ADMIN
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

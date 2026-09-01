"""
ingestion/models.py — Production Data Ingestion & Governance Models for Nyaya Mitra.

Covers:
  - Data Classifications (PUBLIC, INTERNAL, CONFIDENTIAL, HIGHLY_SENSITIVE)
  - Connector Configurations & Health Telemetry
  - Ingestion Batches & Raw Record Provenance
  - Identity Resolution Candidates & Matching Confidence
  - Field Conflicts & Human Review Records
"""

from __future__ import annotations
import uuid
import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


def generate_ingestion_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:14]}"


# ── Data Governance & Classifications ─────────────────────────────────────────

class DataClassification(str, Enum):
    PUBLIC = "PUBLIC"                        # Public cause lists, hearing dates, bench names
    INTERNAL = "INTERNAL"                    # DLSA workflow status, assigned advocate IDs, queue metrics
    CONFIDENTIAL = "CONFIDENTIAL"            # Accused personal identity, relative contact, home address
    HIGHLY_SENSITIVE = "HIGHLY_SENSITIVE"    # Medical vulnerability details, biometric references, juvenile records


# ── Connector Types & Sync Telemetry ──────────────────────────────────────────

class ConnectorType(str, Enum):
    API_PUSH_WEBHOOK = "API_PUSH_WEBHOOK"
    API_POLL_SCHEDULED = "API_POLL_SCHEDULED"
    FILE_IMPORT_CSV = "FILE_IMPORT_CSV"
    FILE_IMPORT_EXCEL = "FILE_IMPORT_EXCEL"
    MANUAL_CONTROLLED_ENTRY = "MANUAL_CONTROLLED_ENTRY"
    SIMULATED_GOV_INTEGRATION = "SIMULATED_GOV_INTEGRATION"


class SyncStatus(str, Enum):
    HEALTHY = "HEALTHY"
    SYNCING = "SYNCING"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


class AuthMethod(str, Enum):
    API_KEY = "API_KEY"
    BEARER_TOKEN = "BEARER_TOKEN"
    MUTUAL_TLS = "MUTUAL_TLS"
    BASIC_AUTH = "BASIC_AUTH"
    SESSION_USER = "SESSION_USER"
    NONE = "NONE"


class ConnectorConfig(BaseModel):
    id: str
    name: str
    display_name: str
    connector_type: ConnectorType
    organization_owner: str
    auth_method: AuthMethod = AuthMethod.NONE
    is_simulated: bool = False
    sync_status: SyncStatus = SyncStatus.HEALTHY
    sync_interval_minutes: int = 60
    last_successful_sync: Optional[str] = None
    records_received: int = 0
    records_rejected: int = 0
    validation_failures: int = 0
    duplicates_detected: int = 0
    conflicts_count: int = 0
    failure_policy: str = "DLQ_AND_ALERT"  # DLQ_AND_ALERT, RETRY_EXPONENTIAL, DROP
    field_mapping: Dict[str, str] = Field(default_factory=dict)
    endpoint_url: Optional[str] = None


# ── Ingestion Batches & Raw Data Provenance ───────────────────────────────────

class IngestionBatch(BaseModel):
    id: str = Field(default_factory=lambda: generate_ingestion_id("batch"))
    connector_id: str
    source_name: str
    source_timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    conflicts_detected: int = 0
    is_demo_batch: bool = False
    status: str = "COMPLETED"  # IN_PROGRESS, COMPLETED, FAILED, PARTIAL


class RawSourceRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_ingestion_id("raw"))
    batch_id: str
    connector_id: str
    payload_hash: str
    raw_payload: Dict[str, Any]
    classification: DataClassification = DataClassification.CONFIDENTIAL
    received_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    validation_errors: List[str] = Field(default_factory=list)
    is_valid: bool = True


# ── Identity Resolution & Probabilistic Deduplication ─────────────────────────

class MatchConfidence(str, Enum):
    CERTAIN = "CERTAIN"        # >= 95% (Exact unique ID match e.g. CNR or Inmate No) -> Auto-merge
    PROBABLE = "PROBABLE"      # 75% - 94% (Composite name + station + relative + age) -> Review recommended
    UNCERTAIN = "UNCERTAIN"    # 60% - 74% (Partial name match + station) -> Mandatory Review Queue
    NEW_ENTITY = "NEW_ENTITY"  # < 60% -> Create distinct new entity


class ResolutionStatus(str, Enum):
    AUTO_MERGED = "AUTO_MERGED"
    PENDING_REVIEW = "PENDING_REVIEW"
    MANUALLY_MERGED = "MANUALLY_MERGED"
    CONFIRMED_SEPARATE = "CONFIRMED_SEPARATE"


class IdentityMatchCandidate(BaseModel):
    id: str = Field(default_factory=lambda: generate_ingestion_id("match"))
    incoming_raw_id: str
    candidate_accused_id: str
    candidate_name: str
    incoming_name: str
    similarity_score: float
    confidence: MatchConfidence
    match_reasons: List[str]
    status: ResolutionStatus = ResolutionStatus.PENDING_REVIEW
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None


# ── Field Conflicts & Human Review Queue ──────────────────────────────────────

class ConflictSeverity(str, Enum):
    LOW = "LOW"            # Non-material (e.g. spelling variation in address)
    MEDIUM = "MEDIUM"      # Moderate operational impact (e.g. contact phone updated)
    CRITICAL = "CRITICAL"  # Material legal impact (e.g. arrest date discrepancy, offense section conflict)


class ConflictStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    ACCEPTED_PROPOSED = "ACCEPTED_PROPOSED"
    KEPT_CANONICAL = "KEPT_CANONICAL"
    OVERRIDDEN_MANUAL = "OVERRIDDEN_MANUAL"


class FieldConflict(BaseModel):
    id: str = Field(default_factory=lambda: generate_ingestion_id("cfl"))
    case_id: str
    accused_id: str
    accused_name: str
    field_name: str
    canonical_value: Any
    canonical_source: str
    canonical_timestamp: str
    proposed_value: Any
    proposed_source: str
    proposed_timestamp: str
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    status: ConflictStatus = ConflictStatus.PENDING_REVIEW
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


# ── Ingestion Telemetry Dashboard Response ────────────────────────────────────

class IngestionDashboardTelemetry(BaseModel):
    connectors: List[ConnectorConfig]
    total_records_ingested: int
    validation_failures_total: int
    conflicts_awaiting_review: int
    identity_merges_pending: int
    active_feeds_count: int
    stale_feeds_count: int
    last_sync_timestamp: str
    demo_mode_active: bool

"""
Domain models and schema definitions for Nyaya Mitra background job processing.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class JobType(str, Enum):
    OCR_DOCUMENT = "OCR_DOCUMENT"
    EMBED_DOCUMENT = "EMBED_DOCUMENT"
    BATCH_INGESTION = "BATCH_INGESTION"
    DISPATCH_NOTIFICATIONS = "DISPATCH_NOTIFICATIONS"
    GENERATE_REPORT = "GENERATE_REPORT"
    AI_SYNTHESIS = "AI_SYNTHESIS"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class ErrorCategory(str, Enum):
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    CORRUPT_PAYLOAD = "CORRUPT_PAYLOAD"
    CIRCUIT_TRIPPED = "CIRCUIT_TRIPPED"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"


class JobRecord(BaseModel):
    id: str
    job_type: JobType
    status: JobStatus
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_category: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[str] = None
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    idempotency_key: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    actor_id: Optional[str] = None
    organization_id: Optional[str] = None


class JobCreateRequest(BaseModel):
    job_type: JobType
    payload: Dict[str, Any] = Field(default_factory=dict)
    max_retries: int = 3
    idempotency_key: Optional[str] = None
    actor_id: Optional[str] = None
    organization_id: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus
    retry_count: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_category: Optional[str] = None
    trace_id: Optional[str] = None


class JobQueueStats(BaseModel):
    total_jobs: int
    queued: int
    processing: int
    completed: int
    failed: int
    dead_letter: int
    active_workers: int

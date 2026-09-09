"""
FastAPI route handlers for background job lifecycle, status queries, and re-queuing.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Query, status

from app.jobs.models import (
    JobType,
    JobStatus,
    JobRecord,
    JobCreateRequest,
    JobResponse,
)
from app.jobs.engine import get_job_engine

router = APIRouter(prefix="/jobs", tags=["Background Jobs & Queue"])


@router.post("/submit", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_job(
    request: JobCreateRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_trace_id: Optional[str] = Header(None, alias="X-Trace-ID"),
    x_span_id: Optional[str] = Header(None, alias="X-Span-ID"),
):
    """Enqueue a long-running background task asynchronously."""
    engine = get_job_engine()
    effective_key = idempotency_key or request.idempotency_key

    job = engine.enqueue_job(
        job_type=request.job_type,
        payload=request.payload,
        idempotency_key=effective_key,
        actor_id=request.actor_id,
        organization_id=request.organization_id,
        trace_id=x_trace_id,
        span_id=x_span_id,
        max_retries=request.max_retries,
    )

    return JobResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        retry_count=job.retry_count,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_ms=job.duration_ms,
        result=job.result,
        error_message=job.error_message,
        error_category=job.error_category,
        trace_id=job.trace_id,
    )


@router.get("/metrics/depth", response_model=Dict[str, int])
def get_queue_depth():
    """Retrieve operational queue depths partitioned by status."""
    engine = get_job_engine()
    return engine.get_queue_depth()


@router.get("/{job_id}", response_model=JobRecord)
def get_job_status(job_id: str):
    """Retrieve current execution status and result payload for a job."""
    engine = get_job_engine()
    job = engine.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return job


@router.get("", response_model=List[JobRecord])
def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    job_type: Optional[JobType] = Query(None, description="Filter by job type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List recent background jobs with optional status and type filters."""
    engine = get_job_engine()
    return engine.list_jobs(
        status=status.value if status else None,
        job_type=job_type.value if job_type else None,
        limit=limit,
        offset=offset,
    )


@router.post("/{job_id}/retry", response_model=JobRecord)
def retry_failed_job(job_id: str):
    """Requeue a failed or dead-letter job for execution."""
    engine = get_job_engine()
    job = engine.retry_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' is not eligible for retry or does not exist.",
        )
    return job

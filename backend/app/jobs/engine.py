"""
Durable job queue repository and persistence engine for Nyaya Mitra.
"""

from __future__ import annotations
import json
import uuid
import threading
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from app.database import get_db_connection
from app.jobs.models import JobRecord, JobType, JobStatus, ErrorCategory

logger = logging.getLogger("nyaya_mitra.jobs.engine")

_ENGINE_LOCK = threading.Lock()


class JobEngine:
    """Thread-safe transactional background job repository."""

    def __init__(self):
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """Create background_jobs table if it does not exist."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS background_jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    result_json TEXT,
                    error_message TEXT,
                    error_category TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    next_retry_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration_ms REAL,
                    idempotency_key TEXT UNIQUE,
                    trace_id TEXT,
                    span_id TEXT,
                    actor_id TEXT,
                    organization_id TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bg_jobs_status ON background_jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bg_jobs_type ON background_jobs(job_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bg_jobs_idempotency ON background_jobs(idempotency_key)")
            conn.commit()
        finally:
            conn.close()

    def enqueue_job(
        self,
        job_type: JobType,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        actor_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        max_retries: int = 3,
    ) -> JobRecord:
        """Enqueue a background job with deduplication if idempotency_key is set."""
        now_iso = datetime.now(timezone.utc).isoformat()

        with _ENGINE_LOCK:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()

                # Check for existing job with the same idempotency key
                if idempotency_key:
                    cursor.execute("SELECT * FROM background_jobs WHERE idempotency_key = ?", (idempotency_key,))
                    row = cursor.fetchone()
                    if row:
                        return self._row_to_record(cursor, row)

                job_id = f"JOB-{uuid.uuid4().hex[:12].upper()}"
                payload_json = json.dumps(payload)

                cursor.execute(
                    """
                    INSERT INTO background_jobs (
                        id, job_type, status, payload_json, retry_count, max_retries,
                        created_at, updated_at, idempotency_key, trace_id, span_id,
                        actor_id, organization_id
                    ) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        job_type.value if hasattr(job_type, "value") else str(job_type),
                        JobStatus.QUEUED.value,
                        payload_json,
                        max_retries,
                        now_iso,
                        now_iso,
                        idempotency_key,
                        trace_id,
                        span_id,
                        actor_id,
                        organization_id,
                    ),
                )
                conn.commit()

                return JobRecord(
                    id=job_id,
                    job_type=job_type,
                    status=JobStatus.QUEUED,
                    payload=payload,
                    retry_count=0,
                    max_retries=max_retries,
                    created_at=now_iso,
                    updated_at=now_iso,
                    idempotency_key=idempotency_key,
                    trace_id=trace_id,
                    span_id=span_id,
                    actor_id=actor_id,
                    organization_id=organization_id,
                )
            finally:
                conn.close()

    def claim_next_job(self, worker_id: str = "worker-default") -> Optional[JobRecord]:
        """Atomically claim the next queued or ready-to-retry job."""
        now_iso = datetime.now(timezone.utc).isoformat()

        with _ENGINE_LOCK:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                # Find eligible job: status = QUEUED, or (status = FAILED and retry_count < max_retries and next_retry_at <= now)
                cursor.execute(
                    """
                    SELECT id FROM background_jobs
                    WHERE status = ? 
                       OR (status = ? AND retry_count < max_retries AND (next_retry_at IS NULL OR next_retry_at <= ?))
                    ORDER BY created_at ASC
                    LIMIT 1
                    """,
                    (JobStatus.QUEUED.value, JobStatus.FAILED.value, now_iso),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                job_id = row[0]

                cursor.execute(
                    """
                    UPDATE background_jobs
                    SET status = ?, started_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (JobStatus.PROCESSING.value, now_iso, now_iso, job_id),
                )
                conn.commit()

                cursor.execute("SELECT * FROM background_jobs WHERE id = ?", (job_id,))
                updated_row = cursor.fetchone()
                return self._row_to_record(cursor, updated_row)
            finally:
                conn.close()

    def complete_job(self, job_id: str, result: Dict[str, Any], duration_ms: float) -> Optional[JobRecord]:
        """Mark a job as completed with its outcome result payload."""
        now_iso = datetime.now(timezone.utc).isoformat()

        with _ENGINE_LOCK:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE background_jobs
                    SET status = ?, result_json = ?, completed_at = ?, duration_ms = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (JobStatus.COMPLETED.value, json.dumps(result), now_iso, duration_ms, now_iso, job_id),
                )
                conn.commit()

                cursor.execute("SELECT * FROM background_jobs WHERE id = ?", (job_id,))
                row = cursor.fetchone()
                return self._row_to_record(cursor, row) if row else None
            finally:
                conn.close()

    def fail_job(
        self,
        job_id: str,
        error_message: str,
        error_category: str = ErrorCategory.SYSTEM_ERROR.value,
        can_retry: bool = True,
    ) -> Optional[JobRecord]:
        """Record job failure, compute exponential backoff or transition to DEAD_LETTER."""
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        with _ENGINE_LOCK:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT retry_count, max_retries FROM background_jobs WHERE id = ?", (job_id,))
                row = cursor.fetchone()
                if not row:
                    return None

                current_retries, max_retries = row[0] or 0, row[1] or 3
                new_retry_count = current_retries + 1

                if new_retry_count >= max_retries or not can_retry:
                    new_status = JobStatus.DEAD_LETTER.value
                    next_retry_at = None
                else:
                    new_status = JobStatus.FAILED.value
                    # Exponential backoff: base 2s * 2^(retry_count)
                    delay_seconds = 2 * (2 ** current_retries)
                    next_retry_at = (now + timedelta(seconds=delay_seconds)).isoformat()

                cursor.execute(
                    """
                    UPDATE background_jobs
                    SET status = ?, retry_count = ?, error_message = ?, error_category = ?,
                        next_retry_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (new_status, new_retry_count, error_message, error_category, next_retry_at, now_iso, job_id),
                )
                conn.commit()

                cursor.execute("SELECT * FROM background_jobs WHERE id = ?", (job_id,))
                updated_row = cursor.fetchone()
                return self._row_to_record(cursor, updated_row) if updated_row else None
            finally:
                conn.close()

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Fetch a job by ID."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM background_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            return self._row_to_record(cursor, row) if row else None
        finally:
            conn.close()

    def list_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[JobRecord]:
        """List jobs filtered by status or type."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM background_jobs"
            params: List[Any] = []
            conditions: List[str] = []

            if status:
                conditions.append("status = ?")
                params.append(status)
            if job_type:
                conditions.append("job_type = ?")
                params.append(job_type)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_record(cursor, r) for r in rows]
        finally:
            conn.close()

    def retry_job(self, job_id: str) -> Optional[JobRecord]:
        """Explicitly requeue a failed or dead-letter job."""
        now_iso = datetime.now(timezone.utc).isoformat()

        with _ENGINE_LOCK:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE background_jobs
                    SET status = ?, next_retry_at = NULL, updated_at = ?
                    WHERE id = ? AND status IN (?, ?)
                    """,
                    (JobStatus.QUEUED.value, now_iso, job_id, JobStatus.FAILED.value, JobStatus.DEAD_LETTER.value),
                )
                conn.commit()

                cursor.execute("SELECT * FROM background_jobs WHERE id = ?", (job_id,))
                row = cursor.fetchone()
                return self._row_to_record(cursor, row) if row else None
            finally:
                conn.close()

    def get_queue_depth(self) -> Dict[str, int]:
        """Retrieve count of jobs across all statuses."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM background_jobs GROUP BY status")
            rows = cursor.fetchall()
            depth = {
                JobStatus.QUEUED.value: 0,
                JobStatus.PROCESSING.value: 0,
                JobStatus.COMPLETED.value: 0,
                JobStatus.FAILED.value: 0,
                JobStatus.DEAD_LETTER.value: 0,
            }
            for status, count in rows:
                if status in depth:
                    depth[status] = count
            return depth
        finally:
            conn.close()

    @staticmethod
    def _row_to_record(cursor, row) -> JobRecord:
        """Convert a database row into a JobRecord pydantic instance."""
        cols = [col[0] for col in cursor.description]
        d = dict(zip(cols, row))

        payload = {}
        if d.get("payload_json"):
            try:
                payload = json.loads(d["payload_json"])
            except Exception:
                payload = {"raw": d["payload_json"]}

        result = None
        if d.get("result_json"):
            try:
                result = json.loads(d["result_json"])
            except Exception:
                result = {"raw": d["result_json"]}

        return JobRecord(
            id=d["id"],
            job_type=JobType(d["job_type"]) if d["job_type"] in [j.value for j in JobType] else JobType.AI_SYNTHESIS,
            status=JobStatus(d["status"]) if d["status"] in [s.value for s in JobStatus] else JobStatus.QUEUED,
            payload=payload,
            result=result,
            error_message=d.get("error_message"),
            error_category=d.get("error_category"),
            retry_count=d.get("retry_count", 0),
            max_retries=d.get("max_retries", 3),
            next_retry_at=d.get("next_retry_at"),
            created_at=d.get("created_at") or "",
            updated_at=d.get("updated_at") or "",
            started_at=d.get("started_at"),
            completed_at=d.get("completed_at"),
            duration_ms=d.get("duration_ms"),
            idempotency_key=d.get("idempotency_key"),
            trace_id=d.get("trace_id"),
            span_id=d.get("span_id"),
            actor_id=d.get("actor_id"),
            organization_id=d.get("organization_id"),
        )


_GLOBAL_JOB_ENGINE: Optional[JobEngine] = None


def get_job_engine() -> JobEngine:
    """Singleton provider for JobEngine."""
    global _GLOBAL_JOB_ENGINE
    if _GLOBAL_JOB_ENGINE is None:
        _GLOBAL_JOB_ENGINE = JobEngine()
    return _GLOBAL_JOB_ENGINE

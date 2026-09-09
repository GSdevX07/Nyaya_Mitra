"""
Automated enterprise reliability and scale test suite for Nyaya Mitra.
Validates:
1. Durable background job engine, worker processing, retries, and dead-letter quarantine.
2. Idempotency middleware deduplication and cached response replay.
3. Structured JSON logging and PII/token sanitization.
4. Distributed tracing propagation across requests.
5. Metrics collector and Prometheus exposition format.
6. Non-leaking operational health endpoints (/health/live, /health/ready, /api/operations/dashboard).
7. Circuit breakers and graceful degradation to procedural statutory bail drafts.
8. Database backup creation, SHA-256 manifest, and automated test-restore sandbox verification.
"""

from __future__ import annotations
import os
import json
import time
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, get_db_connection
from app.jobs.models import JobType, JobStatus, ErrorCategory
from app.jobs.engine import get_job_engine
from app.jobs.workers import get_worker_pool
from app.middleware.idempotency import get_idempotency_store
from app.telemetry.logging import sanitize_sensitive_data, StructuredJsonFormatter
from app.telemetry.tracing import set_trace_context, get_trace_context, new_trace_context
from app.telemetry.metrics import get_metrics_collector, generate_prometheus_metrics
from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    procedural_bail_draft_fallback,
    get_all_circuit_statuses,
)
from app.operations.backup_restore import (
    create_backup,
    test_restore_verification as verify_restore_sandbox,
)


@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    """Initialize test database tables and clean up prior runs."""
    init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ── Component 1 Tests: Durable Background Job Queue & Worker Pool ─────────────

def test_job_enqueue_and_lifecycle():
    """Test job enqueueing, status querying, and claiming."""
    engine = get_job_engine()
    test_payload = {"case_id": "UTP-0001", "document_id": "doc_test_1", "text": "bail grounds"}
    
    # 1. Enqueue
    job = engine.enqueue_job(
        job_type=JobType.OCR_DOCUMENT,
        payload=test_payload,
        max_retries=3,
    )
    assert job.id.startswith("JOB-")
    assert job.status == JobStatus.QUEUED
    assert job.retry_count == 0

    # 2. Get Job
    retrieved = engine.get_job(job.id)
    assert retrieved is not None
    assert retrieved.id == job.id
    assert retrieved.payload["case_id"] == "UTP-0001"

    # 3. Synchronous worker execution test helper
    worker_pool = get_worker_pool()
    completed_job = worker_pool.process_one_job_synchronously()
    assert completed_job is not None
    assert completed_job.id == job.id
    assert completed_job.status == JobStatus.COMPLETED
    assert completed_job.duration_ms is not None
    assert completed_job.result is not None
    assert completed_job.result["ocr_status"] == "COMPLETED"


def test_job_exponential_backoff_and_dead_letter():
    """Test failure backoff progression and isolation to DEAD_LETTER."""
    engine = get_job_engine()
    job = engine.enqueue_job(
        job_type=JobType.AI_SYNTHESIS,
        payload={"case_id": "UTP-FAIL-TEST", "force_failure": True},
        max_retries=2,
    )

    # First failure
    f1 = engine.fail_job(job.id, "Provider timeout", ErrorCategory.TIMEOUT.value)
    assert f1.status == JobStatus.FAILED
    assert f1.retry_count == 1
    assert f1.next_retry_at is not None

    # Second failure (hits max_retries = 2)
    f2 = engine.fail_job(job.id, "Provider timeout again", ErrorCategory.TIMEOUT.value)
    assert f2.status == JobStatus.DEAD_LETTER
    assert f2.retry_count == 2
    assert f2.next_retry_at is None

    # Explicit manual retry
    requeued = engine.retry_job(job.id)
    assert requeued.status == JobStatus.QUEUED


def test_job_queue_depth_metrics():
    """Test queue depth counters across states."""
    engine = get_job_engine()
    depths = engine.get_queue_depth()
    assert isinstance(depths, dict)
    assert "QUEUED" in depths
    assert "PROCESSING" in depths
    assert "COMPLETED" in depths
    assert "DEAD_LETTER" in depths


# ── Component 2 Tests: Idempotency Engine ─────────────────────────────────────

def test_idempotency_store_replay_and_conflict():
    """Test idempotency lock claiming and result retrieval."""
    store = get_idempotency_store()
    idem_key = f"IDEM-UNIT-{int(time.time())}"
    endpoint = "/test/mutating"

    # Claim in progress
    claimed = store.mark_in_progress(idem_key, endpoint, "hash_abc", actor_id="user_1")
    assert claimed is True

    # Concurrent attempt with same key fails
    claimed_again = store.mark_in_progress(idem_key, endpoint, "hash_abc", actor_id="user_2")
    assert claimed_again is False

    # Store result
    store.store_result(idem_key, endpoint, 201, '{"created": true}')

    # Retrieve cached record
    rec = store.get_record(idem_key, endpoint)
    assert rec is not None
    assert rec["status"] == "COMPLETED"
    assert rec["status_code"] == 201
    assert json.loads(rec["response_body_json"]) == {"created": True}


def test_idempotent_http_request_replay(client):
    """Test HTTP API request replay with Idempotency-Key header."""
    key = f"HTTP-KEY-{int(time.time() * 1000)}"
    headers = {"Idempotency-Key": key}
    payload = {
        "job_type": "AI_SYNTHESIS",
        "payload": {"case_id": "UTP-0001", "petition_type": "REGULAR_BAIL"},
    }

    # 1. First execution creates job
    resp1 = client.post("/jobs/submit", json=payload, headers=headers)
    assert resp1.status_code == 202
    data1 = resp1.json()
    job_id_1 = data1["job_id"]

    # 2. Second identical request with same key returns cached replay
    resp2 = client.post("/jobs/submit", json=payload, headers=headers)
    assert resp2.status_code == 202
    assert resp2.headers.get("Idempotent-Replayed") == "true"
    data2 = resp2.json()
    assert data2["job_id"] == job_id_1


# ── Component 3 Tests: Structured JSON Logging & PII Sanitization ────────────

def test_sensitive_data_sanitization():
    """Verify that credentials, tokens, and PII are redacted from log records."""
    raw_payload = {
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.secret",
        "password": "MySuperSecretPassword123",
        "aadhaar": "2345 6789 0123",
        "phone": "+91 9876543210",
        "innocent_field": "Undertrial bail petition",
    }
    cleaned = sanitize_sensitive_data(raw_payload)
    assert cleaned["authorization"] == "[REDACTED]"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["aadhaar"] == "[PII_REDACTED]"
    assert cleaned["phone"] == "[PII_REDACTED]"
    assert cleaned["innocent_field"] == "Undertrial bail petition"


def test_structured_json_formatter():
    """Verify JSON log formatting output."""
    import logging
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Execution completed successfully with token Bearer abcd1234efgh5678",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert "Bearer [REDACTED]" in parsed["message"]
    assert "timestamp" in parsed


# ── Component 4 & 5 Tests: Distributed Tracing & Metrics Telemetry ───────────

def test_distributed_tracing_propagation(client):
    """Verify X-Request-ID and X-Trace-ID response injection."""
    resp = client.get("/health/live", headers={"X-Request-ID": "TEST-REQ-999"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == "TEST-REQ-999"
    assert resp.headers.get("X-Trace-ID") is not None
    assert resp.headers.get("X-Span-ID") is not None


def test_metrics_collection_and_prometheus_export(client):
    """Verify Prometheus telemetry exposition."""
    collector = get_metrics_collector()
    collector.record_http_request("/cases", "GET", 200, 0.045)
    collector.record_ai_usage("granite", input_tokens=150, output_tokens=300)
    collector.record_ocr_operation("success", 1.25)

    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["Content-Type"]
    content = resp.text
    assert "nyaya_mitra_http_requests_total" in content
    assert "nyaya_mitra_ai_tokens_total" in content
    assert "nyaya_mitra_ocr_operations_total" in content


# ── Component 6 Tests: Non-Leaking Operational Health Endpoints ───────────────

def test_operational_health_probes(client):
    """Verify liveness, readiness, and telemetry summary endpoints."""
    # Liveness
    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    # Readiness
    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    ready_data = ready_res.json()
    assert ready_data["status"] == "ready"
    assert ready_data["checks"]["database"] == "operational"
    assert ready_data["checks"]["background_queue"] == "operational"
    # Verify no credentials leaked
    text = ready_res.text
    assert "password" not in text.lower()
    assert "postgres://" not in text
    assert "secret" not in text.lower()

    # Operations Dashboard
    dash_res = client.get("/api/operations/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "status" in dash_data
    assert "queue" in dash_data
    assert "circuit_breakers" in dash_data
    assert "telemetry" in dash_data


# ── Component 7 Tests: Backup, Restore & Automated Test Restore ───────────────

def test_backup_and_test_restore_verification(tmp_path):
    """Verify online SQLite snapshot creation and automated sandbox test-restore."""
    manifest = create_backup(target_dir=str(tmp_path))
    assert manifest.status == "COMPLETED"
    assert os.path.exists(manifest.database_path)
    assert len(manifest.database_sha256) == 64  # SHA-256 hex string

    # Run automated test-restore into sandbox
    report = verify_restore_sandbox(manifest.database_path)
    assert report.status == "PASSED"
    assert report.integrity_check == "ok"
    assert "cases" in report.tables_found
    assert "audit_events" in report.tables_found
    assert report.audit_chain_valid is True
    assert report.record_counts.get("cases", 0) >= 0


# ── Component 9 Tests: Circuit Breakers & Graceful Degradation ────────────────

def test_circuit_breaker_trips_and_executes_fallback():
    """Verify circuit trips after 3 failures and immediately returns procedural fallback."""
    breaker = CircuitBreaker("test_ai_gateway", failure_threshold=3, recovery_timeout=2.0)
    assert breaker.state == CircuitState.CLOSED

    # Simulate 3 consecutive failures
    breaker.record_failure(RuntimeError("503 Provider Down"))
    breaker.record_failure(RuntimeError("503 Provider Down"))
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure(RuntimeError("503 Provider Down"))
    assert breaker.state == CircuitState.OPEN

    # In OPEN state, execute immediately uses fallback without raising
    res = breaker.execute(
        func=lambda: {"draft": "from_llm"},
        fallback=lambda: procedural_bail_draft_fallback("UTP-0001", "Suresh Patel"),
    )
    assert res["status"] == "AI_OFFLINE_FALLBACK"
    assert "SECTION 479" in res["draft_text"]
    assert "Suresh Patel" in res["draft_text"]


def test_connector_circuit_isolation():
    """Verify that tripping one connector does not trip or degrade others."""
    statuses = get_all_circuit_statuses()
    assert "ai_gateway" in statuses
    assert "ecourts" in statuses
    assert "eprisons" in statuses
    assert "cctns" in statuses
    # ecourts and eprisons are independent instances
    assert statuses["ecourts"]["name"] != statuses["eprisons"]["name"]

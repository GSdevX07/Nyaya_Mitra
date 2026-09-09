# Nyaya Mitra Operational Incident Runbook

## 1. Scope & Objective

This document defines standard operating procedures (SOPs) for site reliability engineers (SRE), system administrators, and on-call operational engineers responding to production alerts and degradations across Nyaya Mitra.

---

## 2. Incident Response Matrix

| Severity | Definition | Response Time (SLA) | Escalate To |
|---|---|---|---|
| SEV-1 | Core database unavailable, audit ledger tampering detected, full API outage | < 15 minutes | Lead Systems Architect & Legal Directorate |
| SEV-2 | Background worker stall, AI provider timeout, connector circuit tripped | < 30 minutes | Platform SRE & Operations Lead |
| SEV-3 | Queue depth elevated, isolated non-critical route latency | < 2 hours | Duty Engineer |
| SEV-4 | Minor telemetry discrepancy, scheduled maintenance alerts | Next business day | DevOps Team |

---

## 3. Standard Operating Procedures (SOPs)

### SOP-01: AI Provider Outage & High Latency (Circuit Breaker Tripped)

#### Symptoms:
- Alert: `CircuitBreakerTripped: ai_gateway` or `NyayaMitraAIErrorsSpike`.
- Telemetry: Gauge `nyaya_mitra_circuit_breaker_state{service="ai_gateway"}` equals `2.0` (OPEN).
- HTTP endpoints return status `AI_OFFLINE_FALLBACK` on bail draft generation.

#### Diagnosis & Verification:
1. Check breaker status via operations dashboard:
   ```bash
   curl -s http://127.0.0.1:8000/api/operations/dashboard | jq .circuit_breakers.ai_gateway
   ```
2. Verify if upstream provider (Granite / Groq / OpenAI) is degraded or unreachable:
   ```bash
   curl -I https://api.groq.com/openai/v1/models
   ```

#### Remediation Steps:
1. **Confirm Fallback Mode**: Verify that bail applications are still generating procedural statutory templates rather than throwing 500 errors.
2. **Provider Failover**:
   - If Groq is degraded, update `LLM_PROVIDER_OVERRIDE` in `.env` or configuration to fallback provider (`granite` or `mock`).
   - Reload API pods with zero downtime:
     ```bash
     docker service update --env-add LLM_PROVIDER_OVERRIDE=granite nyaya_mitra_api
     ```
3. **Breaker Reset**:
   - Once upstream connectivity is verified, the circuit breaker will transition to `HALF_OPEN` automatically after 30 seconds.
   - Alternatively, trigger manual probe via API.

---

### SOP-02: Background Job Queue Saturation & Dead-Letter Drain

#### Symptoms:
- Alert: `QueueDepthHigh: background_jobs > 100` or `DeadLetterJobsDetected`.
- Telemetry: Gauge `nyaya_mitra_job_queue_depth{status="dead_letter"} > 0`.

#### Diagnosis & Verification:
1. Inspect queue distribution:
   ```bash
   curl -s http://127.0.0.1:8000/jobs/metrics/depth
   ```
2. Query recent dead-letter jobs:
   ```bash
   curl -s "http://127.0.0.1:8000/jobs?status=DEAD_LETTER&limit=10" | jq .
   ```

#### Remediation Steps:
1. **Analyze Error Category**:
   - `TIMEOUT`: Increase worker concurrency or worker instance count.
   - `CORRUPT_PAYLOAD`: Investigate originating client payload and quarantine invalid document.
   - `CIRCUIT_TRIPPED`: Wait for downstream service recovery.
2. **Scale Workers**:
   - Increase worker replica count or adjust concurrency in worker configuration.
3. **Re-queue Dead-Letter Jobs**:
   - Once the underlying issue is resolved, requeue dead-letter tasks:
     ```bash
     curl -X POST http://127.0.0.1:8000/jobs/JOB-XXXXXX/retry
     ```

---

### SOP-03: High Database Latency & Connection Lockup

#### Symptoms:
- Alert: `DatabaseQueryLatencyHigh: p95 > 500ms` or `SQLiteDatabaseLocked`.
- Readiness probe returns HTTP 503 (`/health/ready`).

#### Diagnosis & Verification:
1. Query operational readiness probe:
   ```bash
   curl -s http://127.0.0.1:8000/health/ready
   ```
2. Check file lock or database busy timeouts:
   ```bash
   sqlite3 nyaya_mitra.db "PRAGMA busy_timeout;"
   ```

#### Remediation Steps:
1. In SQLite local environments: Ensure `PRAGMA journal_mode = WAL;` is enabled to allow concurrent readers with non-blocking writers.
2. In PostgreSQL production environments:
   - Check active query locks:
     ```sql
     SELECT pid, query, age(clock_timestamp(), query_start) FROM pg_stat_activity WHERE state != 'idle';
     ```
   - Terminate long-running blocking query:
     ```sql
     SELECT pg_terminate_backend(blocking_pid);
     ```

---

### SOP-04: External Court / Prison Connector Failure

#### Symptoms:
- Alert: `ConnectorCircuitTripped: ecourts` or `eprisons`.
- External sync jobs failing, but core judicial and case management functions remain operative.

#### Diagnosis & Verification:
1. Check connector circuit states:
   ```bash
   curl -s http://127.0.0.1:8000/api/operations/dashboard | jq .circuit_breakers
   ```

#### Remediation Steps:
1. Verify that case viewing, accused records, and manual document uploads continue without interruption (circuit isolation guarantees zero cross-service degradation).
2. If eCourts is down, switch intake mode to manual CSV docket upload or offline batch queue.
3. When the external portal returns, re-enable sync jobs.

---

### SOP-05: Audit Ledger Hash Integrity Alert

#### Symptoms:
- Alert: `AuditLedgerTamperDetected` or `AuditChainIntegrityCheckFailed`.
- Automated test-restore verification returns `audit_chain_valid = False`.

#### Diagnosis & Verification:
1. Execute ledger integrity verification:
   ```bash
   python -c "from app.repositories.audit_repository import verify_ledger_integrity; print(verify_ledger_integrity())"
   ```
2. Identify the broken sequence number and tampered event hash.

#### Remediation Steps:
1. **Quarantine Active Database**: Immediately freeze write traffic to prevent cascaded damage.
2. **Restore Verified Snapshot**:
   - Locate the most recent verified backup from the automated backup archive:
     ```bash
     python scripts/backup_restore.py test-restore backups/nyaya_mitra_LATEST.db
     ```
   - If verified, perform safe restore:
     ```bash
     python scripts/backup_restore.py restore backups/nyaya_mitra_LATEST.db
     ```
3. **Escalate to Legal Directorate**: File an incident report with cryptographic discrepancy details for forensic review.

---

### SOP-06: Emergency Secret & Credential Rotation

#### Trigger:
- Leaked credentials, compromised API keys, or routine 90-day key rotation cycle.

#### Remediation Steps:
1. Rotate database master passwords in platform secret store (AWS Secrets Manager / Vault).
2. Generate fresh JWT signing keys:
   ```bash
   openssl rand -hex 32
   ```
3. Update environment configuration (`SECRET_KEY`, `SUPABASE_SERVICE_KEY`).
4. Perform rolling restart of API pods.
5. Invalidate active user sessions by incrementing token version counter.

# Nyaya Mitra Capacity Plan & Sizing Specifications

## 1. Executive Summary

This document establishes the production capacity targets, throughput baselines, resource sizing models, and auto-scaling triggers for Nyaya Mitra across Indian judicial, prison, and legal aid environments.

---

## 2. Workload & Capacity Projections

### 2.1 Concurrency & User Tiers
| Tier | Stakeholder Role | Concurrent Users (Peak) | Typical Session Duration | Primary Operations |
|---|---|---|---|---|
| Tier 1 | Legal Aid Defense Advocates | 150 | 45 minutes | Case inspection, bail draft generation, evidence review |
| Tier 2 | DLSA Legal Aid Officers | 50 | 30 minutes | Intake triage, Section 479 eligibility approval, court handoffs |
| Tier 3 | Jail Superintendents & Staff | 30 | 20 minutes | Custody verification, batch intake, release dispatch |
| Tier 4 | System Admins & Auditors | 20 | 15 minutes | Health monitoring, audit ledger verification, queue telemetry |
| **Total** | **All Enterprise Users** | **250** | -- | Peak concurrent sessions |

### 2.2 Data Volume & Storage Horizons
| Storage Dimension | Current Baseline | 12-Month Target | 36-Month Target | Storage Engine |
|---|---|---|---|---|
| Undertrial & Convict Cases | 1,000 | 100,000 | 500,000 | PostgreSQL (Supabase) / SQLite |
| Case Dockets & Evidence Docs | 5,000 | 500,000 | 2,500,000 | S3 / MinIO Object Storage |
| Audit Ledger Records | 25,000 | 2,500,000 | 15,000,000 | Append-Only Cryptographic Table |
| Vector Embeddings Chunks | 10,000 | 1,000,000 | 5,000,000 | Chroma / pgvector |
| Background Job History | 5,000 | 1,000,000 | 5,000,000 | Partitioned Background Jobs Table |

---

## 3. Latency & Throughput Service Level Objectives (SLOs)

### 3.1 Latency Quantiles (Target SLOs)
- **Synchronous Read Endpoints** (`GET /cases`, `GET /cases/{id}`, `GET /health/ready`):
  - 50th percentile (p50): < 80 ms
  - 95th percentile (p95): < 250 ms
  - 99th percentile (p99): < 500 ms
- **Asynchronous Intake Endpoints** (`POST /jobs/submit`, `POST /cases` with Idempotency-Key):
  - 50th percentile (p50): < 50 ms
  - 95th percentile (p95): < 120 ms
  - 99th percentile (p99): < 200 ms
- **Background Worker Job Duration**:
  - OCR Document (5-page PDF): < 8.0 s
  - Document Vectorization & Embedding: < 3.0 s
  - Bail Application AI Synthesis: < 4.0 s (Fallback procedural template: < 20 ms)
  - Batch Spreadsheet Ingestion (500 rows): < 15.0 s

### 3.2 Throughput Capacities
- Web API Intake: 300 Requests / Second sustained; 750 RPS burst.
- Background Job Execution: 50 concurrent jobs / worker pool instance.
- Daily Intake Throughput: 10,000 new intake cases / day.

---

## 4. Hardware Sizing & Cluster Topology

### 4.1 Production Multi-Node Deployment
```
                                 ┌────────────────────────┐
                                 │ Cloudflare / Load Bal  │
                                 │   (TLS Term + WAF)     │
                                 └───────────┬────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │
                       ▼                                           ▼
          ┌─────────────────────────┐                 ┌─────────────────────────┐
          │  API Pod 1 (FastAPI)    │                 │  API Pod 2 (FastAPI)    │
          │  4 vCPU, 8 GB RAM       │                 │  4 vCPU, 8 GB RAM       │
          └────────────┬────────────┘                 └────────────┬────────────┘
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             │
         ┌───────────────────────────────────┼───────────────────────────────────┐
         │                                   │                                   │
         ▼                                   ▼                                   ▼
┌───────────────────┐               ┌───────────────────┐               ┌───────────────────┐
│ Database Node     │               │ Background Worker │               │ Chroma / Vector   │
│ 8 vCPU, 32 GB RAM │               │ 8 vCPU, 16 GB RAM │               │ 4 vCPU, 16 GB RAM │
│ NVMe SSD 500 GB   │               │ Concurrency: 8    │               │ SSD 100 GB        │
└───────────────────┘               └───────────────────┘               └───────────────────┘
```

### 4.2 Auto-Scaling Rules
- **API Pods Horizontal Pod Autoscaler (HPA)**:
  - Scale out when CPU utilization > 70% or active HTTP connection count > 200 per replica.
  - Min replicas: 2; Max replicas: 8.
- **Worker Pool Autoscaler**:
  - Scale out when `queue_depth(QUEUED)` > 50 jobs for more than 60 seconds.
  - Scale in when `queue_depth(QUEUED)` < 5 jobs for more than 300 seconds.
  - Min replicas: 2; Max replicas: 6.

---

## 5. Storage Partitioning & Archival Rules

1. **Audit Ledger Partitioning**:
   - Table `audit_events` partitioned monthly by `timestamp`.
   - Historical partitions older than 7 years moved to cold compressed read-only storage.
2. **Background Jobs Retention**:
   - Jobs in `COMPLETED` status older than 30 days are purged by scheduled vacuum.
   - Jobs in `DEAD_LETTER` are retained for 90 days for forensic inspection.
3. **Idempotent Requests Retention**:
   - Records with `expires_at < NOW()` are cleared daily via background cleaner.

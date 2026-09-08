# Nyaya Mitra External Integration Readiness Checklist

## Institutional Governance & Security Standard for External Source Connectors

> **MANDATORY POLICY DIRECTIVE**:  
> Nyaya Mitra **strictly prohibits** claiming active or production access to government databases (e-Courts, e-Prisons, CCTNS, State Prosecution, DLSA/NALSA) until every technical, legal, and operational gateway documented in this checklist has been formally executed, verified, and audited.  
> In all current deployments where official Memoranda of Understanding (MoUs) or production API credentials are not active, the system operates exclusively in **`[SANDBOX_SIMULATED]`** mode with zero destructive modifications to canonical legal dossiers.

---

## 1. Current Source System Integration Status Matrix

| External Institutional Source | Connecting Agency / Directorate | Target Protocol / Standard | Current Status | Production Access Blocker |
| :--- | :--- | :--- | :--- | :--- |
| **e-Courts Judicial Services** | e-Committee, Supreme Court of India / NIC | REST JSON / NJDG CIS Open API v2 | `[SANDBOX_SIMULATED]` | Formal e-Committee API agreement & VPN tunnel approval pending. |
| **e-Prisons National PMS** | National Informatics Centre (NIC) / Prison Directorate | REST JSON / mTLS Webhook | `[SANDBOX_SIMULATED]` | Prison Directorate Data Sharing Agreement & static IP whitelisting pending. |
| **Police CCTNS Network** | National Crime Records Bureau (NCRB) / State Police | REST Webhook / HMAC-SHA256 Signed | `[SANDBOX_SIMULATED]` | State Police Commissionerate MoU & token vault authorization pending. |
| **Directorate of Prosecution** | State Directorate of Prosecution (e-Prosecution) | REST JSON API / OAuth2 Client | `[SANDBOX_SIMULATED]` | State Law Department data access clearance & prosecutor directory binding pending. |
| **DLSA / KSLSA Legal Aid (LADCS)**| NALSA / State Legal Services Authorities | REST API / LADCS Integration Gateway | `[SANDBOX_SIMULATED]` | Statutory SLSA operational circular & remand clinic coordination pending. |
| **Structured Spreadsheet Hub** | District Legal Services Authority (DLSA) Intake | Multipart CSV / Excel Parser | `[OPERATIONAL_LOCAL]` | None (local role-gated intake desk operational). |
| **Manual Intake Gateway** | Jail Desk / Remand Advocate Intake Form | Controlled REST Intake Gateway | `[OPERATIONAL_LOCAL]` | None (role-authorized supervisor intake operational). |

---

## 2. The 4-Tier Integration Readiness Framework

Before any connector transitions from `[SANDBOX_SIMULATED]` to `[ONLINE]`, it must pass all 4 tiers of verification:

### Tier 1: Legal Mandate & Data Governance Readiness
- [ ] **Bilateral Memorandum of Understanding (MoU)**: Formally signed data access agreement between the State Legal Services Authority (SLSA) and the respective institutional authority (e-Committee, Prison Directorate, Police Commissionerate, or Directorate of Prosecution).
- [ ] **Statutory Privacy Compliance**: Verified adherence to the **Digital Personal Data Protection (DPDP) Act, 2023** and **Information Technology Act, 2000 (Section 43A)** regarding undertrial prisoner personally identifiable information (PII).
- [ ] **Purpose Limitation & Data Minimization**: Ingestion limited strictly to docket identifiers (CNR), arrest dates, custody duration, charged sections, and hearing listings necessary for Section 479 BNSS / Section 436A CrPC evaluation.
- [ ] **Non-Destructive Ingestion Rule**: Source system synchronization implemented as versioned event ingestion. Direct destructive updates to canonical case records are prohibited; discrepancies must route to the human conflict reconciliation queue.

### Tier 2: Technical Architecture & Security Protocols
- [ ] **Encrypted Credential Vault**: Zero plaintext access tokens or secrets stored in databases or configuration files. Tokens resolved exclusively via secure environment variables or vault keys.
- [ ] **Zero Browser Exposure**: Access tokens, client secrets, and signing keys are never serialized in API responses or visible in browser network traffic. Frontend receives only masked identifiers (e.g. `vault:***4f8a`).
- [ ] **HMAC-SHA256 Request Signing**: All outbound institutional requests contain signed verification headers:
  - `X-Nyaya-Signature`: Hex-encoded HMAC-SHA256 signature of `method + path + timestamp + nonce + payload_hash`.
  - `X-Nyaya-Timestamp`: UTC ISO-8601 timestamp (preventing replay attacks outside a 5-minute window).
  - `X-Nyaya-Nonce`: Unique cryptographically random UUID v4 per request.
  - `X-Nyaya-Payload-Hash`: SHA-256 hash of the outbound request body.
- [ ] **Transport Security**: Mutual TLS (mTLS) with government-issued PKI certificates where required, with TLS 1.3 enforced.
- [ ] **Network Perimeter Security**: Static IP whitelisting and dedicated Gov-cloud VPN tunnel termination.

### Tier 3: Conformance Testing & Sandbox Validation
- [ ] **Token Bucket Rate Limiting**: Enforced rate limiter per connector (e.g. 60 req/min for e-Courts, 30 req/min for CCTNS) with graceful 429 backpressure handling.
- [ ] **Cursor & Offset Pagination**: Support for high-volume record batches with boundary validation and deadlock prevention.
- [ ] **Exponential Backoff & Jitter**: Automated retry engine for transient network interruptions (500, 502, 503, 504, 429) with randomized jitter to prevent thundering herds.
- [ ] **Idempotency & Replay Protection**: Deterministic SHA-256 payload hashing and `Idempotency-Key` tracking preventing duplicate event ingestion.
- [ ] **Synthetic Marker Gate**: Production mode (`DEMO_MODE=false`) strictly rejects synthetic/mock markers, ensuring simulated data cannot contaminate live judicial dossiers.

### Tier 4: Operational Readiness & Go-Live Protocol
- [ ] **Connector Health Telemetry**: Real-time monitoring of operational status (`ONLINE`, `DEGRADED`, `OFFLINE`, `SANDBOX_SIMULATED`), round-trip latency (ms), error rates (%), processed/rejected record counts, and credential expiry tracking.
- [ ] **Manual Conflict Reconciliation Workflow**: Operational human review queue where discrepancies in hearing dates, arrest dates, custody days, or case identifiers (CNR) are inspected side-by-side by authorized legal supervisors before canonical commitment.
- [ ] **Tamper-Evident Outbound Audit Logging**: Every sync trigger, outbound request, latency measurement, and human reconciliation decision is logged to the immutable audit ledger.
- [ ] **Graceful Degraded / Offline Fallback**: In the event of government gateway downtime, connector automatically transitions to `DEGRADED` or `OFFLINE` status without crashing core legal workflows or blocking user navigation.

---

## 3. Discrepancy Reconciliation Policies

When an external connector ingests data that differs from existing canonical records, the following policies apply:

1. **Arrest Date Discrepancy (`CRITICAL`)**:
   - Because arrest dates dictate statutory bail eligibility under Section 479 BNSS (half/one-third sentence calculation), incoming values are never auto-committed.
   - The discrepancy is logged as a `CRITICAL` field conflict in `integration_conflicts`.
   - The Supervising Legal Officer must review the physical remand order and select **Keep Canonical**, **Adopt Incoming**, or enter a **Manual Override** with mandatory justification notes.
2. **Hearing Date Discrepancy (`CRITICAL`)**:
   - Disagreements between e-Courts docket listings and local court production diaries create an immediate `CRITICAL` conflict.
   - The human reviewer verifies the cause list and commits the resolved date to `hearings_schedule`.
3. **Case Identifier / CNR Mismatch (`CRITICAL`)**:
   - Changes in official CNR numbers trigger mandatory identity re-verification to prevent cross-prisoner docket pollution.
4. **Offense Sections Mismatch (`MEDIUM`)**:
   - Discrepancies between police FIR sections and court chargesheet sections are flagged for counsel review to assess whether newly added sections alter bail eligibility parameters.

---

## 4. Production Transition Sign-Off Protocol

A connector may be switched from `is_simulated = True` to `is_simulated = False` only after:
1. Formal legal sign-off from the SLSA Member Secretary or authorized Registrar.
2. Independent third-party vulnerability and penetration testing (VAPT) certification.
3. Successful completion of 7 consecutive days of error-free sandbox synchronization in staging.
4. Verification by the Platform Administrator that production credentials exist in the secure vault.

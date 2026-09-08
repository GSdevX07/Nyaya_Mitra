# Nyaya Mitra: Prioritized Security & Privacy Remediation Plan

**Document Version**: 1.0  
**Classification**: Risk-Ranked Engineering Roadmap  
**Framework Alignment**: Standard Security Risk Assessment Methodology

---

## 1. Executive Summary

This remediation plan organizes system-wide hardening actions into four risk-ranked phases: Critical (P0), High (P1), Medium (P2), and Low / Defense-in-Depth (P3). Each remediation includes the target risk, affected components, and validation criteria.

---

## 2. Risk-Ranked Action Items

### Priority P0: Critical Remediation (Immediate Implementation)
These vulnerabilities present immediate risk of cross-tenant data exposure, unauthorized legal mutation, or secret leakage.

| ID | Vulnerability / Threat | Affected Component | Technical Remediation | Validation Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **P0-1** | Production Boot with Insecure Secrets | `auth/config.py` | Fail-closed startup check: throw `RuntimeError` if `JWT_SECRET` is default or `DEMO_MODE=true` in production mode. | Test `APP_ENV=production` fails to start with demo secret. |
| **P0-2** | Privilege Leak to Platform Admin | `main.py`, `workflow/` | Strictly prohibit `PLATFORM_ADMIN` from case approvals, court filing, and identity merge. | Automated tests assert 403 Forbidden for Admin on all legal actions. |
| **P0-3** | Predictable Document Download Paths | `main.py`, `documents/` | Replace raw URLs with cryptographic HMAC-SHA256 time-expiring tokens. | Unsigned or expired links return 401/403. |
| **P0-4** | Malicious File Uploads | `security_scanner.py` | Enforce binary magic byte checks, size limits, and PDF stream decompressive malware scanning. | Macro-laced or executable files are quarantined. |

---

### Priority P1: High Remediation (Core Security Boundaries)
These controls establish data privacy boundaries and tamper-resistant accountability.

| ID | Vulnerability / Threat | Affected Component | Technical Remediation | Validation Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **P1-1** | Unredacted Medical & Psychiatric Data | `security/classification.py` | Tier 1 field-level filter: Medical details replaced with encrypted envelope for non-medical roles. | Police, Jail, and External Advocates receive redacted medical envelopes. |
| **P1-2** | PII Leak in Public Rosters & Reports | `security/classification.py` | Tier 2 field-level filter: Permanent address and phone numbers redacted from police and analytics. | Accused profile returns privacy-controlled placeholders. |
| **P1-3** | Insecure Audit Log Modifications | `audit_repository.py` | Cryptographic SHA-256 hash chaining with automated verification endpoint. | Ledger traversal detects any altered record or missing sequence number. |
| **P1-4** | Untracked Citizen Data Processing | `security/consent.py` | Affirmative consent tracking with IP, timestamp, notice version, and withdrawal endpoint. | Accused/Family can opt in and revoke consent with audit logging. |

---

### Priority P2: Medium Remediation (Operational & Governance Controls)
These controls address insider threats, data hoarding, and prompt safety.

| ID | Vulnerability / Threat | Affected Component | Technical Remediation | Validation Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **P2-1** | Prompt Injection & Model Extraction | `ai/policies.py` | Neutralize prompt hijacking patterns; encapsulate untrusted evidence in `<inert_document_data>`. | Adversarial inputs neutralized before dispatch to external LLMs. |
| **P2-2** | Indefinite Data Retention | `security/retention.py` | Configurable retention engine with purge evaluation and clear statutory validation disclaimers. | Retention evaluation dry-run accurately identifies expired payloads. |
| **P2-3** | Unmonitored Access Anomalies | `security/incident_response.py` | Automated incident triggers for brute-force spikes, bulk downloads, and connector hash mismatches. | 10 rapid downloads or 5 failed logins trigger automated containment alert. |

---

### Priority P3: Defense-in-Depth (Platform Hardening & CI/CD)
System hygiene and automated regression prevention.

| ID | Vulnerability / Threat | Affected Component | Technical Remediation | Validation Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **P3-1** | Missing HTTP Security Headers | `main.py` | Middleware injecting CSP, HSTS, X-Frame-Options, X-Content-Type-Options. | Verified on API responses. |
| **P3-2** | Lack of Automated CI Security Gates | `.github/workflows/` | GitHub Actions workflow with `pip-audit`, `npm audit`, Bandit SAST, and secret scanning. | CI pipeline passes on commits. |
| **P3-3** | Sequential Case ID Enumeration | `main.py` | Fail-closed 404 responses for unauthorized case IDs without revealing case existence. | Out-of-district case ID returns generic 404. |

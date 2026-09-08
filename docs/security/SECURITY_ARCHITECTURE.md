# Nyaya Mitra: Security Architecture & Defense-in-Depth Specification

**Document Version**: 1.0  
**Classification**: System Security Architecture  
**Disclaimer**: Architectural specification. Formal statutory compliance assessments must be performed independently prior to deployment in certified government environments.

---

## 1. Architectural Principles

Nyaya Mitra is built upon five foundational security tenets tailored for Indian criminal justice IT infrastructure:

1. **Principle of Least Consequence**:
   A compromise of technical administrative credentials (`PLATFORM_ADMIN`) must never compromise judicial outcome integrity or authorize substantive legal actions. Consequential powers (case approval, court filing, identity resolution) reside exclusively with statutory officers (`SUPERVISING_LEGAL_OFFICER`, `DLSA_OFFICER`).

2. **Defense in Depth**:
   Security controls operate across all tiers: TLS 1.3 transport security, HTTP security headers, JWT validation, ABAC route scoping, field-level data classification filters, cryptographic audit hashing, and binary document screening.

3. **Statutory Fail-Closed Operation**:
   If an identity, district, police station, or jail facility match cannot be established with mathematical certainty, access is denied (`403 Forbidden` or `404 Not Found`).

4. **Tamper-Evident Accountability**:
   All state mutations and sensitive access events are chained into a cryptographic SHA-256 Merkle ledger, enabling mathematical proof of zero tampering.

5. **Privacy Engineering & Data Minimization**:
   Sensitive PII and medical vulnerabilities are isolated into encrypted envelopes, exposed only to designated medical legal officers, and redacted from all operational rosters.

---

## 2. Multi-Layer Security Controls

```
Layer 1: Edge & Transport
  └── TLS 1.3 / HTTPS
  └── Security Headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
  └── Origin Validation & CORS Guard

Layer 2: Identity & Authentication
  └── PBKDF2-SHA256 Password Store
  └── Progressive Brute-Force Delays & Account Lockouts
  └── Short-Lived JWTs (60 min) + Server-Side JTI Revocation

Layer 3: Authorization & Scoping (ABAC)
  └── Role-Based Access Control (9 Canonical Institutional Roles)
  └── Territorial & Jurisdictional Scoping (District, State, Station, Facility)
  └── Case Assignment Binding (Defense Counsel Docket Verification)

Layer 4: Field-Level Data Classification & Redaction
  └── Tier 1: Medical / Psychiatric / Biometric Data Envelope
  └── Tier 2: Sensitive Identity PII (Address, Phone, Relatives, Aadhaar)
  └── Tier 3: Restricted Legal Work Product (Draft Petitions, Notes)
  └── Tier 4: Operational Metadata (Court, Remand, FIR, Sections)

Layer 5: AI & Document Safety Boundary
  └── Binary Magic Byte Verification
  └── FlateDecode PDF Decompression & Active Script Elimination
  └── Inert XML Document Encapsulation (<inert_document_data>)
  └── Prompt Injection Detection & Model Leakage Shield

Layer 6: Cryptographic Audit & Ledger
  └── SHA-256 Merkle / Linked-List Hash Chaining
  └── Dual-Write Persistence (Local SQLite + Remote Supabase)
  └── Tamper-Verification Traversal Engine
```

---

## 3. Cryptographic Storage & Encryption Specifications

### 3.1 Data in Transit
- **Protocol**: Transport Layer Security (TLS) 1.3 preferred; TLS 1.2 minimum.
- **Cipher Suites**: ECDHE-ECDSA-AES256-GCM-SHA384, ECDHE-RSA-AES256-GCM-SHA384.
- **HTTP Strict Transport Security (HSTS)**: `max-age=31536000; includeSubDomains`.

### 3.2 Data at Rest
- **Database Storage**: AES-256 encryption at rest provided by host storage volume / PostgreSQL Transparent Data Encryption (TDE) / cloud encrypted SSD.
- **Sensitive Envelope Encryption**: Highly sensitive fields (Aadhaar placeholders, family contact numbers, medical diagnoses) support column-level encryption via AES-256-GCM prior to database write.
- **Document Store**: Uploaded file streams are encrypted with unique per-file initialization vectors (IVs) and stored in isolated storage volumes.

### 3.3 Secrets Management
- In production, secrets (`JWT_SECRET`, database connection strings, Supabase keys, LLM provider tokens) must never be loaded from plaintext disk `.env` files.
- The platform provides a `CloudVaultSecretManager` interface capable of integrating with AWS Secrets Manager, Azure Key Vault, Google Cloud Secret Manager, or HashiCorp Vault.

---

## 4. Field-Level Data Classification Architecture

| Classification Tier | Data Attributes Included | Authorized Roles | Redaction Strategy |
| :--- | :--- | :--- | :--- |
| **Tier 1: Medical & Biometric** | Health flag, chronic conditions, psychiatric notes, disability status, biometric records | `SUPERVISING_LEGAL_OFFICER`, `DLSA_OFFICER`, Self-Accused | Completely replaced with `[RESTRICTED SENSITIVE MEDICAL ENVELOPE]` for Police, Jail, Advocates, Public |
| **Tier 2: Sensitive Identity PII** | Permanent residential address, personal mobile phone, family contact details, national ID tokens | Assigned Counsel, DLSA Officer, Self-Accused, Family Guardian | Masked with `[RESTRICTED - PRIVACY CONTROLLED]` for Police rosters, State overview, and Auditors |
| **Tier 3: Legal Work Product** | Section 479 unfiled petition drafts, counsel defense strategy, supervisory evaluation notes | Assigned Defense Counsel, Supervising Legal Officer | Completely omitted from Admin, Police, Jail, and Auditor views |
| **Tier 4: Operational Metadata** | FIR number, court name, remand dates, hearing schedules, charge sections, custody days | All authenticated staff within district/facility scope | Unmasked for authorized operational staff |

---

## 5. Audit Logging Architecture

Nyaya Mitra implements an append-only audit ledger with cryptographic sequence links:

```
[Genesis Hash]
      │
      ▼
[Event 1] ──► SHA-256(event_id_1 | timestamp | actor | action | details | Genesis Hash | Seq 1)
      │
      ▼
[Event 2] ──► SHA-256(event_id_2 | timestamp | actor | action | details | Hash of Event 1 | Seq 2)
      │
      ▼
[Event 3] ──► SHA-256(event_id_3 | timestamp | actor | action | details | Hash of Event 2 | Seq 3)
```

If an attacker modifies any event record, details payload, or timestamp in the database, the hash verification traversal immediately detects a hash mismatch at that exact sequence number, invalidating the entire subsequent chain.

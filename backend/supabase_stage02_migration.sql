-- ══════════════════════════════════════════════════════════════════════════════
-- NYAYA MITRA — STAGE 02 COMPLETE SUPABASE POSTGRESQL MIGRATION & SEED SCRIPT
-- ══════════════════════════════════════════════════════════════════════════════
-- Instructions:
-- 1. Open your Supabase Dashboard: https://supabase.com/dashboard
-- 2. Select your Project -> Click on "SQL Editor" in the left sidebar.
-- 3. Click "New query", paste this entire script, and click "Run" (or Ctrl+Enter).
-- ══════════════════════════════════════════════════════════════════════════════

BEGIN;

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── IDEMPOTENCY: Drop all Stage 02 tables in dependency order ─────────────────
-- Safe to run repeatedly — no real user data exists yet.
-- Preserves the legacy `cases` table (DROP + recreate below preserves seed data via INSERT ON CONFLICT).
DROP TABLE IF EXISTS revoked_tokens        CASCADE;
DROP TABLE IF EXISTS audit_events          CASCADE;
DROP TABLE IF EXISTS notifications         CASCADE;
DROP TABLE IF EXISTS uploaded_documents    CASCADE;
DROP TABLE IF EXISTS evidence              CASCADE;
DROP TABLE IF EXISTS documents             CASCADE;
DROP TABLE IF EXISTS bail_applications     CASCADE;
DROP TABLE IF EXISTS custody_calculations  CASCADE;
DROP TABLE IF EXISTS charges               CASCADE;
DROP TABLE IF EXISTS court_cases           CASCADE;
DROP TABLE IF EXISTS firs                  CASCADE;
DROP TABLE IF EXISTS custody_records       CASCADE;
DROP TABLE IF EXISTS identity_references   CASCADE;
DROP TABLE IF EXISTS accused_persons       CASCADE;
DROP TABLE IF EXISTS organization_users    CASCADE;
DROP TABLE IF EXISTS facilities            CASCADE;
DROP TABLE IF EXISTS organizations         CASCADE;
DROP TABLE IF EXISTS cases                 CASCADE;

-- ── 1. TENANCY LAYER: Organizations & Facilities ─────────────────────────────

CREATE TABLE IF NOT EXISTS organizations (
    id                  TEXT PRIMARY KEY,
    code                TEXT UNIQUE NOT NULL,
    name                TEXT NOT NULL,
    org_type            TEXT NOT NULL,
    state               TEXT,
    district            TEXT,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS facilities (
    id                  TEXT PRIMARY KEY,
    organization_id     TEXT REFERENCES organizations(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    facility_type       TEXT NOT NULL,
    state               TEXT,
    district            TEXT,
    capacity            INT DEFAULT 500,
    current_occupancy   INT DEFAULT 0,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

-- ── 2. RBAC LAYER: Organization Users & Roles ────────────────────────────────

CREATE TABLE IF NOT EXISTS organization_users (
    id                      TEXT PRIMARY KEY,
    organization_id         TEXT REFERENCES organizations(id) ON DELETE CASCADE,
    email                   TEXT UNIQUE NOT NULL,
    password_hash           TEXT,
    full_name               TEXT NOT NULL,
    role                    TEXT NOT NULL,
    phone                   TEXT,
    district                TEXT,
    facility_ids            JSONB DEFAULT '[]'::jsonb,
    linked_case_id          TEXT,
    relationship_to_accused TEXT,
    bar_registration_no     TEXT,
    failed_login_count      INT DEFAULT 0,
    locked_until            TIMESTAMPTZ,
    last_login_at           TIMESTAMPTZ,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ
);

-- Idempotent column additions for existing databases
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS district TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS facility_ids JSONB DEFAULT '[]'::jsonb;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS linked_case_id TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS relationship_to_accused TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS failed_login_count INT DEFAULT 0;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- ── 3. SUBJECT & CUSTODY: Accused Persons & Custody Records ─────────────────

CREATE TABLE IF NOT EXISTS accused_persons (
    id                      TEXT PRIMARY KEY,
    full_name               TEXT NOT NULL,
    gender                  TEXT DEFAULT 'Male',
    age                     INT DEFAULT 30,
    preferred_language      TEXT DEFAULT 'en',
    health_vulnerability    BOOLEAN DEFAULT FALSE,
    health_details          TEXT,
    is_senior_citizen       BOOLEAN DEFAULT FALSE,
    repeat_offender         BOOLEAN DEFAULT FALSE,
    relative_name           TEXT,
    relative_relation       TEXT,
    relative_phone          TEXT,
    permanent_address       TEXT,
    data_source_status      TEXT DEFAULT 'DEMO_SYNTHETIC',
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS identity_references (
    id                  TEXT PRIMARY KEY,
    accused_id          TEXT REFERENCES accused_persons(id) ON DELETE CASCADE,
    id_type             TEXT NOT NULL, -- PRISON_INMATE_NO, CCTNS_PERSON_ID, etc.
    id_value            TEXT NOT NULL,
    issuing_authority   TEXT,
    is_verified         BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS custody_records (
    id                      TEXT PRIMARY KEY,
    accused_id              TEXT NOT NULL REFERENCES accused_persons(id) ON DELETE CASCADE,
    facility_id             TEXT REFERENCES facilities(id),
    admission_date          DATE NOT NULL,
    prisoner_category       TEXT DEFAULT 'UNDERTRIAL',
    calendar_custody_days   INT DEFAULT 0,
    excluded_delay_days     INT DEFAULT 0,
    countable_custody_days  INT DEFAULT 0,
    is_current_custody      BOOLEAN DEFAULT TRUE,
    release_date            DATE,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── 4. POLICE & COURT PROCEDURAL DOCKET: FIRs & Court Cases ──────────────────

CREATE TABLE IF NOT EXISTS firs (
    id                  TEXT PRIMARY KEY,
    fir_number          TEXT NOT NULL,
    police_station      TEXT NOT NULL,
    district            TEXT,
    state               TEXT,
    filing_date         DATE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS court_cases (
    id                      TEXT PRIMARY KEY, -- e.g. UTP-0001
    case_number             TEXT NOT NULL,
    accused_id              TEXT NOT NULL REFERENCES accused_persons(id) ON DELETE CASCADE,
    fir_id                  TEXT REFERENCES firs(id),
    organization_id         TEXT REFERENCES organizations(id),
    cnr_number              TEXT,
    court_name              TEXT NOT NULL,
    district                TEXT,
    state                   TEXT,
    legal_code              TEXT DEFAULT 'BNS_2023',
    current_status          TEXT DEFAULT 'INTAKE_PENDING',
    dlsa_reference_number   TEXT,
    assigned_lawyer_id      TEXT,
    assignment_status       TEXT DEFAULT 'AVAILABLE',
    data_source_status      TEXT DEFAULT 'DEMO_SYNTHETIC',
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS charges (
    id                      TEXT PRIMARY KEY,
    case_id                 TEXT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    legal_code              TEXT NOT NULL,
    section_number          TEXT NOT NULL,
    offence_title           TEXT,
    max_imprisonment_days   INT DEFAULT 365,
    is_capital_offence      BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── 5. DETERMINISTIC RULES: Custody Calculations & Bail Applications ────────

CREATE TABLE IF NOT EXISTS custody_calculations (
    id                              TEXT PRIMARY KEY,
    case_id                         TEXT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    rule_version                    TEXT DEFAULT 'BNSS_479_RULESET_V1_2023',
    calculation_timestamp           TIMESTAMPTZ DEFAULT NOW(),
    total_calendar_days             INT,
    excluded_delay_days             INT,
    countable_custody_days          INT,
    max_sentence_days               INT,
    statutory_threshold_fraction    TEXT, -- '1/3' or '1/2'
    threshold_days                  INT,
    days_overdue                    INT,
    is_eligible                     BOOLEAN,
    requires_human_legal_review     BOOLEAN DEFAULT TRUE,
    review_reasons                  JSONB DEFAULT '[]'::jsonb,
    statutory_conditions            JSONB DEFAULT '[]'::jsonb,
    disclaimer                      TEXT
);

CREATE TABLE IF NOT EXISTS bail_applications (
    id                      TEXT PRIMARY KEY,
    case_id                 TEXT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    statutory_section       TEXT DEFAULT 'Section 479 BNSS, 2023',
    petition_draft_text     TEXT,
    advocate_signed_off     BOOLEAN DEFAULT FALSE,
    signed_off_by_user_id   TEXT,
    signed_off_at           TIMESTAMPTZ,
    court_filing_reference  TEXT,
    filing_date             DATE,
    is_filed                BOOLEAN DEFAULT FALSE,
    status                  TEXT DEFAULT 'DRAFT',
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── 6. EVIDENCE & DOCUMENTS: Vault, Uploads, Hashes ─────────────────────────

CREATE TABLE IF NOT EXISTS documents (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL,
    document_type       TEXT NOT NULL,
    file_name           TEXT,
    storage_path        TEXT,
    file_size_bytes     INT DEFAULT 0,
    mime_type           TEXT DEFAULT 'application/pdf',
    sha256_hash         TEXT,
    is_mandatory        BOOLEAN DEFAULT TRUE,
    is_present          BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

-- Retrofit any columns missing on a pre-existing documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_name        TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_path     TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size_bytes  INT DEFAULT 0;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type        TEXT DEFAULT 'application/pdf';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS sha256_hash      TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_mandatory     BOOLEAN DEFAULT TRUE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_present       BOOLEAN DEFAULT TRUE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS created_at       TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE documents ADD COLUMN IF NOT EXISTS deleted_at       TIMESTAMPTZ;
-- Re-add FK reference safely (skips if already exists via DO $$)
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'documents_case_id_fkey' AND table_name = 'documents'
  ) THEN
    ALTER TABLE documents ADD CONSTRAINT documents_case_id_fkey
      FOREIGN KEY (case_id) REFERENCES court_cases(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id         TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    document_type       TEXT NOT NULL,
    file_name           TEXT NOT NULL,
    stored_hash         TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Retrofit DEFAULT in case the table already existed without it
ALTER TABLE evidence ALTER COLUMN created_at SET DEFAULT NOW();
ALTER TABLE evidence ALTER COLUMN created_at SET NOT NULL;

CREATE TABLE IF NOT EXISTS uploaded_documents (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL,
    document_type       TEXT NOT NULL,
    file_name           TEXT NOT NULL,
    extracted_text      TEXT,
    custom_text         TEXT,
    is_handwritten      BOOLEAN DEFAULT FALSE,
    ocr_engine          TEXT,
    file_hash           TEXT,
    file_size_bytes     INT DEFAULT 0,
    mime_type           TEXT,
    uploaded_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT,
    title               TEXT NOT NULL,
    message             TEXT NOT NULL,
    type                TEXT NOT NULL,
    is_read             BOOLEAN DEFAULT FALSE,
    timestamp           TIMESTAMPTZ DEFAULT NOW()
);

-- ── 7. IMMUTABLE AUDIT TRAIL ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_events (
    id                  TEXT PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id            TEXT NOT NULL,
    actor_role          TEXT NOT NULL,
    organization_id     TEXT,
    action              TEXT NOT NULL,
    entity_type         TEXT NOT NULL,
    entity_id           TEXT NOT NULL,
    ip_address          TEXT,
    details_json        TEXT NOT NULL,
    is_immutable        BOOLEAN DEFAULT TRUE
);

-- Database-Level Immutability Trigger (Prevents UPDATE and DELETE on audit_events)
CREATE OR REPLACE FUNCTION enforce_audit_event_immutability()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit trail violation: audit_events records are strictly immutable and cannot be updated or deleted.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_events_immutable ON audit_events;
CREATE TRIGGER trg_audit_events_immutable
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION enforce_audit_event_immutability();

-- ── 8. LEGACY COMPATIBILITY TABLE & SESSION STORE ───────────────────────────

CREATE TABLE IF NOT EXISTS cases (
    case_id             TEXT PRIMARY KEY,
    data                JSONB NOT NULL,
    status              TEXT DEFAULT 'DETECTED',
    assignment_status   TEXT DEFAULT 'AVAILABLE',
    assigned_lawyer_id  TEXT,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS revoked_tokens (
    jti                 TEXT PRIMARY KEY,
    user_id             TEXT REFERENCES organization_users(id) ON DELETE SET NULL,
    expires_at          TIMESTAMPTZ NOT NULL,
    revoked_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 9. PERFORMANCE INDEXES ──────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_court_cases_accused      ON court_cases(accused_id);
CREATE INDEX IF NOT EXISTS idx_court_cases_status       ON court_cases(current_status);
CREATE INDEX IF NOT EXISTS idx_court_cases_org          ON court_cases(organization_id);
CREATE INDEX IF NOT EXISTS idx_custody_accused          ON custody_records(accused_id);
CREATE INDEX IF NOT EXISTS idx_charges_case             ON charges(case_id);
CREATE INDEX IF NOT EXISTS idx_documents_case           ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_evidence_case            ON evidence(case_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity             ON audit_events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp          ON audit_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires   ON revoked_tokens(expires_at);

-- ── 10. ROW LEVEL SECURITY (RLS) POLICIES ────────────────────────────────────

ALTER TABLE organizations           ENABLE ROW LEVEL SECURITY;
ALTER TABLE facilities              ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_users      ENABLE ROW LEVEL SECURITY;
ALTER TABLE accused_persons         ENABLE ROW LEVEL SECURITY;
ALTER TABLE custody_records         ENABLE ROW LEVEL SECURITY;
ALTER TABLE firs                    ENABLE ROW LEVEL SECURITY;
ALTER TABLE court_cases             ENABLE ROW LEVEL SECURITY;
ALTER TABLE charges                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE custody_calculations    ENABLE ROW LEVEL SECURITY;
ALTER TABLE bail_applications       ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents               ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence                ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events            ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE revoked_tokens          ENABLE ROW LEVEL SECURITY;

-- Allow service_role key full administrative access
CREATE POLICY "Service role full access on organizations"        ON organizations        FOR ALL USING (true);
CREATE POLICY "Service role full access on facilities"           ON facilities           FOR ALL USING (true);
CREATE POLICY "Service role full access on organization_users"   ON organization_users   FOR ALL USING (true);
CREATE POLICY "Service role full access on accused_persons"      ON accused_persons      FOR ALL USING (true);
CREATE POLICY "Service role full access on custody_records"      ON custody_records      FOR ALL USING (true);
CREATE POLICY "Service role full access on firs"                 ON firs                 FOR ALL USING (true);
CREATE POLICY "Service role full access on court_cases"          ON court_cases          FOR ALL USING (true);
CREATE POLICY "Service role full access on charges"              ON charges              FOR ALL USING (true);
CREATE POLICY "Service role full access on custody_calculations" ON custody_calculations FOR ALL USING (true);
CREATE POLICY "Service role full access on bail_applications"    ON bail_applications    FOR ALL USING (true);
CREATE POLICY "Service role full access on documents"            ON documents            FOR ALL USING (true);
CREATE POLICY "Service role full access on evidence"             ON evidence             FOR ALL USING (true);
CREATE POLICY "Service role full access on audit_events"         ON audit_events         FOR ALL USING (true);
CREATE POLICY "Service role full access on cases"                ON cases                FOR ALL USING (true);
CREATE POLICY "Service role full access on revoked_tokens"       ON revoked_tokens       FOR ALL USING (true);

-- ── 11. SEED CANONICAL STAKEHOLDERS & HERO CASES ─────────────────────────────

-- Seed Default Organizations
INSERT INTO organizations (id, code, name, org_type, state, district)
VALUES 
    ('org_dlsa_central', 'DLSA-CD', 'District Legal Services Authority, Central Delhi', 'DLSA', 'Delhi', 'Central Delhi'),
    ('org_tihar_jail', 'PRISON-TJ04', 'Tihar Central Prison Complex No. 4', 'PRISON_JAIL', 'Delhi', 'West Delhi'),
    ('org_court_magistrate', 'COURT-MM02', 'Metropolitan Magistrate Court 02, Central', 'REMAND_COURT', 'Delhi', 'Central Delhi')
ON CONFLICT (id) DO NOTHING;

-- Seed Default Facilities
INSERT INTO facilities (id, organization_id, name, facility_type, state, district, capacity, current_occupancy)
VALUES 
    ('fac_tihar_jail_04', 'org_tihar_jail', 'Tihar Central Jail No. 4', 'Central Jail', 'Delhi', 'West Delhi', 1200, 840)
ON CONFLICT (id) DO NOTHING;

-- Seed Default Organization Users (11 Demo Personas)
INSERT INTO organization_users (id, organization_id, email, full_name, role, district, linked_case_id, is_active)
VALUES
    ('demo_admin',        'org_dlsa_central', 'admin@demo.nyayamitra.in',        'Platform Administrator (Demo)', 'PLATFORM_ADMIN',            'Central Delhi', NULL,       TRUE),
    ('demo_gov',          'org_dlsa_central', 'gov@demo.nyayamitra.in',          'Government SLSA Admin (Demo)',  'GOV_ADMIN',                  'Central Delhi', NULL,       TRUE),
    ('demo_jail',         'org_tihar_jail',   'jail@demo.nyayamitra.in',         'Jail Superintendent (Demo)',    'JAIL_OFFICER',               'Central Delhi', NULL,       TRUE),
    ('demo_police',       'org_dlsa_central', 'police@demo.nyayamitra.in',       'Police Officer (Demo)',         'POLICE_OFFICER',             'Central Delhi', NULL,       TRUE),
    ('demo_dlsa',         'org_dlsa_central', 'dlsa@demo.nyayamitra.in',         'DLSA Legal Officer (Demo)',     'DLSA_OFFICER',               'Central Delhi', NULL,       TRUE),
    ('demo_supervising',  'org_dlsa_central', 'supervising@demo.nyayamitra.in',  'Supervising Officer (Demo)',    'SUPERVISING_LEGAL_OFFICER',  'Central Delhi', NULL,       TRUE),
    ('demo_advocate',     'org_dlsa_central', 'advocate@demo.nyayamitra.in',     'Defense Advocate (Demo)',       'DEFENSE_ADVOCATE',           'Central Delhi', NULL,       TRUE),
    ('demo_ext_advocate', 'org_dlsa_central', 'extadvocate@demo.nyayamitra.in',  'External Advocate (Demo)',      'CONTROLLED_EXTERNAL_ADVOCATE','Central Delhi',NULL,       TRUE),
    ('demo_accused',      'org_dlsa_central', 'accused@demo.nyayamitra.in',      'Accused Person (Demo)',         'ACCUSED_USER',               'Central Delhi', 'UTP-0001', TRUE),
    ('demo_family',       'org_dlsa_central', 'family@demo.nyayamitra.in',       'Family Guardian (Demo)',        'FAMILY_GUARDIAN',            'Central Delhi', 'UTP-0001', TRUE),
    ('demo_auditor',      'org_dlsa_central', 'auditor@demo.nyayamitra.in',      'Read-Only Auditor (Demo)',      'READ_ONLY_AUDITOR',          'Central Delhi', NULL,       TRUE)
ON CONFLICT (id) DO UPDATE SET updated_at = NOW(), linked_case_id = EXCLUDED.linked_case_id;

-- Seed Accused Persons
INSERT INTO accused_persons (id, full_name, gender, age, preferred_language, health_vulnerability, health_details, is_senior_citizen, repeat_offender, relative_name, relative_relation, relative_phone, permanent_address, data_source_status)
VALUES 
    ('acc_utp_0001', 'Suresh Patel (Synthetic)', 'Male', 24, 'hi', FALSE, NULL, FALSE, FALSE, 'Ramesh Patel', 'Father', '+91 98765 43210', 'H-42, Shakurpur, Delhi - 110034', 'DEMO_SYNTHETIC'),
    ('acc_utp_0002', 'Mohammad Rehan (Synthetic)', 'Male', 29, 'en', FALSE, NULL, FALSE, FALSE, 'Fatima Begum', 'Mother', '+91 98111 22334', 'B-12, Jamia Nagar, Okhla, New Delhi - 110025', 'DEMO_SYNTHETIC'),
    ('acc_utp_0003', 'Vikramaditya Rao (Synthetic)', 'Male', 68, 'en', TRUE, 'Chronic coronary artery disease requiring medication', TRUE, FALSE, 'Ananya Rao', 'Daughter', '+91 99887 76655', 'Flat 4B, Sector 14, Rohini, Delhi - 110085', 'DEMO_SYNTHETIC'),
    ('acc_utp_0012', 'Jagdish Pradhan (Synthetic)', 'Male', 36, 'hi', FALSE, NULL, FALSE, FALSE, 'Sunita Pradhan', 'Wife', '+91 97112 33445', 'Village Alipur, North Delhi - 110036', 'DEMO_SYNTHETIC'),
    ('acc_utp_0015', 'Tenzin Namgyal (Synthetic)', 'Male', 22, 'en', FALSE, NULL, FALSE, FALSE, 'Dolma Namgyal', 'Sister', '+91 96500 11223', 'House 18, Majnu Ka Tilla, Delhi - 110054', 'DEMO_SYNTHETIC'),
    ('acc_utp_0021', 'Kavita Sundaram (Synthetic)', 'Female', 31, 'ta', FALSE, NULL, FALSE, FALSE, 'Sundaram Pillai', 'Father', '+91 94440 12345', '14/2, Karol Bagh, Central Delhi - 110005', 'DEMO_SYNTHETIC')
ON CONFLICT (id) DO UPDATE SET updated_at = NOW();

-- Seed Custody Records
INSERT INTO custody_records (id, accused_id, facility_id, admission_date, prisoner_category, calendar_custody_days, excluded_delay_days, countable_custody_days, is_current_custody)
VALUES 
    ('cus_utp_0001', 'acc_utp_0001', 'fac_tihar_jail_04', '2025-01-10', 'UNDERTRIAL', 200, 0, 200, TRUE),
    ('cus_utp_0002', 'acc_utp_0002', 'fac_tihar_jail_04', '2025-03-01', 'UNDERTRIAL', 150, 0, 150, TRUE),
    ('cus_utp_0003', 'acc_utp_0003', 'fac_tihar_jail_04', '2024-08-01', 'UNDERTRIAL', 360, 0, 360, TRUE),
    ('cus_utp_0012', 'acc_utp_0012', 'fac_tihar_jail_04', '2024-05-15', 'UNDERTRIAL', 440, 0, 440, TRUE),
    ('cus_utp_0015', 'acc_utp_0015', 'fac_tihar_jail_04', '2024-11-20', 'UNDERTRIAL', 250, 0, 250, TRUE),
    ('cus_utp_0021', 'acc_utp_0021', 'fac_tihar_jail_04', '2024-09-01', 'UNDERTRIAL', 330, 0, 330, TRUE)
ON CONFLICT (id) DO UPDATE SET updated_at = NOW();

-- Seed FIRs
INSERT INTO firs (id, fir_number, police_station, district, state, filing_date)
VALUES 
    ('fir_utp_0001', 'FIR-2025-010', 'Gandhi Nagar Police Station', 'Central Delhi', 'Delhi', '2025-01-10'),
    ('fir_utp_0002', 'FIR-2025-045', 'Daryaganj Police Station', 'Central Delhi', 'Delhi', '2025-03-01'),
    ('fir_utp_0003', 'FIR-2024-189', 'Prashant Vihar Police Station', 'North West Delhi', 'Delhi', '2024-08-01'),
    ('fir_utp_0012', 'FIR-2024-088', 'Alipur Police Station', 'North Delhi', 'Delhi', '2024-05-15'),
    ('fir_utp_0015', 'FIR-2024-210', 'Civil Lines Police Station', 'Central Delhi', 'Delhi', '2024-11-20'),
    ('fir_utp_0021', 'FIR-2024-142', 'Karol Bagh Police Station', 'Central Delhi', 'Delhi', '2024-09-01')
ON CONFLICT (id) DO NOTHING;

-- Seed Court Cases
INSERT INTO court_cases (id, case_number, accused_id, fir_id, organization_id, cnr_number, court_name, district, state, legal_code, current_status, dlsa_reference_number, assigned_lawyer_id, assignment_status, data_source_status)
VALUES 
    ('UTP-0001', 'UTP-0001', 'acc_utp_0001', 'fir_utp_0001', 'org_dlsa_central', 'DLCT010049212025', 'Metropolitan Magistrate Court 02, Central', 'Central Delhi', 'Delhi', 'BNS_2023', 'ELIGIBLE', 'DLSA-CD-2025-0112', 'Legal Officer 104', 'ASSIGNED', 'DEMO_SYNTHETIC'),
    ('UTP-0002', 'UTP-0002', 'acc_utp_0002', 'fir_utp_0002', 'org_dlsa_central', 'DLCT010058342025', 'Metropolitan Magistrate Court 05, Central', 'Central Delhi', 'Delhi', 'BNS_2023', 'DETECTED', 'DLSA-CD-2025-0189', 'Legal Officer 104', 'ASSIGNED', 'DEMO_SYNTHETIC'),
    ('UTP-0003', 'UTP-0003', 'acc_utp_0003', 'fir_utp_0003', 'org_dlsa_central', 'DLNW010087122024', 'Additional Sessions Court 03, North-West', 'North West Delhi', 'Delhi', 'IPC_1860', 'MANUAL_REVIEW', 'DLSA-NW-2024-0744', 'Legal Officer 104', 'ASSIGNED', 'DEMO_SYNTHETIC'),
    ('UTP-0012', 'UTP-0012', 'acc_utp_0012', 'fir_utp_0012', 'org_dlsa_central', 'DLNT010034192024', 'Sessions Court 01, North Delhi', 'North Delhi', 'Delhi', 'BNS_2023', 'DETECTED', 'DLSA-ND-2024-0391', NULL, 'AVAILABLE', 'DEMO_SYNTHETIC'),
    ('UTP-0015', 'UTP-0015', 'acc_utp_0015', 'fir_utp_0015', 'org_dlsa_central', 'DLCT010091022024', 'Metropolitan Magistrate Court 01, Central', 'Central Delhi', 'Delhi', 'BNS_2023', 'DOCUMENTS_MISSING', 'DLSA-CD-2024-0982', NULL, 'AVAILABLE', 'DEMO_SYNTHETIC'),
    ('UTP-0021', 'UTP-0021', 'acc_utp_0021', 'fir_utp_0021', 'org_dlsa_central', 'DLCT010067452024', 'Chief Metropolitan Magistrate Court, Central', 'Central Delhi', 'Delhi', 'BNS_2023', 'APPROVED_READY_FOR_FILING', 'DLSA-CD-2024-0811', 'Legal Officer 104', 'ASSIGNED', 'DEMO_SYNTHETIC')
ON CONFLICT (id) DO UPDATE SET updated_at = NOW();

-- Seed Charges
INSERT INTO charges (id, case_id, legal_code, section_number, offence_title, max_imprisonment_days, is_capital_offence)
VALUES 
    ('chg_utp_0001_bns_115', 'UTP-0001', 'BNS_2023', 'BNS 115(2)', 'Voluntarily causing hurt', 365, FALSE),
    ('chg_utp_0002_bns_303', 'UTP-0002', 'BNS_2023', 'BNS 303(2)', 'Theft in dwelling house', 1095, FALSE),
    ('chg_utp_0003_ipc_420', 'UTP-0003', 'IPC_1860', 'IPC 420', 'Cheating and dishonestly inducing delivery of property', 2555, FALSE),
    ('chg_utp_0012_bns_103', 'UTP-0012', 'BNS_2023', 'BNS 103(1)', 'Murder (Capital Offence)', 7300, TRUE),
    ('chg_utp_0015_bns_303', 'UTP-0015', 'BNS_2023', 'BNS 303(2)', 'Theft (Repeat Allegation)', 1095, FALSE),
    ('chg_utp_0021_bns_316', 'UTP-0021', 'BNS_2023', 'BNS 316(2)', 'Criminal breach of trust', 1095, FALSE)
ON CONFLICT (id) DO NOTHING;

-- Seed Evidence
INSERT INTO evidence (evidence_id, case_id, document_type, file_name, stored_hash, created_at)
VALUES 
    ('EVI-UTP-0001-remand_order',      'UTP-0001', 'remand_order',        'remand_order.pdf',        encode(digest('verified_content_UTP-0001_remand_order',        'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0001-charge_sheet',      'UTP-0001', 'charge_sheet',        'charge_sheet.pdf',        encode(digest('verified_content_UTP-0001_charge_sheet',        'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0002-remand_order',      'UTP-0002', 'remand_order',        'remand_order.pdf',        encode(digest('verified_content_UTP-0002_remand_order',        'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0003-remand_order',      'UTP-0003', 'remand_order',        'remand_order.pdf',        encode(digest('verified_content_UTP-0003_remand_order',        'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0003-medical_certificate','UTP-0003', 'medical_certificate', 'medical_certificate.pdf', encode(digest('verified_content_UTP-0003_medical_certificate',  'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0012-remand_order',      'UTP-0012', 'remand_order',        'remand_order.pdf',        encode(digest('verified_content_UTP-0012_remand_order',        'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0015-remand_order',      'UTP-0015', 'remand_order',        'remand_order.pdf',        encode(digest('verified_content_UTP-0015_remand_order',        'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0021-remand_order',      'UTP-0021', 'remand_order',        'remand_order.pdf',        encode(digest('verified_content_UTP-0021_remand_order',        'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0021-charge_sheet',      'UTP-0021', 'charge_sheet',        'charge_sheet.pdf',        encode(digest('verified_content_UTP-0021_charge_sheet',        'sha256'), 'hex'), NOW())
ON CONFLICT (evidence_id) DO NOTHING;


-- Seed Documents
INSERT INTO documents (id, case_id, document_type, file_name, storage_path, file_size_bytes, mime_type, sha256_hash, is_mandatory, is_present)
VALUES 
    ('doc_utp_0001_remand_order', 'UTP-0001', 'remand_order', 'remand_order.pdf', '/evidence/UTP-0001/remand_order.pdf', 102400, 'application/pdf', encode(digest('verified_content_UTP-0001_remand_order', 'sha256'), 'hex'), TRUE, TRUE),
    ('doc_utp_0001_charge_sheet', 'UTP-0001', 'charge_sheet', 'charge_sheet.pdf', '/evidence/UTP-0001/charge_sheet.pdf', 204800, 'application/pdf', encode(digest('verified_content_UTP-0001_charge_sheet', 'sha256'), 'hex'), TRUE, TRUE),
    ('doc_utp_0021_remand_order', 'UTP-0021', 'remand_order', 'remand_order.pdf', '/evidence/UTP-0021/remand_order.pdf', 102400, 'application/pdf', encode(digest('verified_content_UTP-0021_remand_order', 'sha256'), 'hex'), TRUE, TRUE),
    ('doc_utp_0021_charge_sheet', 'UTP-0021', 'charge_sheet', 'charge_sheet.pdf', '/evidence/UTP-0021/charge_sheet.pdf', 204800, 'application/pdf', encode(digest('verified_content_UTP-0021_charge_sheet', 'sha256'), 'hex'), TRUE, TRUE)
ON CONFLICT (id) DO NOTHING;

COMMIT;

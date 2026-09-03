-- ══════════════════════════════════════════════════════════════════════════════
-- NYAYA MITRA — STAGE 04 COMPLETE CANONICAL POSTGRESQL SYNTHETIC SEED SCRIPT
-- ══════════════════════════════════════════════════════════════════════════════
-- Instructions for Supabase:
--   1. Open your Supabase Dashboard: https://supabase.com/dashboard
--   2. Select your Project -> Click on "SQL Editor" in the left sidebar.
--   3. Click "New query", paste this entire script, and click "Run" (or Ctrl+Enter).
--
-- Features:
--   - 100% Idempotent (safe to re-run anytime via ON CONFLICT DO UPDATE).
--   - Sets up all 11 Role Demo Accounts with authentic bcrypt password "Demo@12345".
--   - Sets up all 6 Canonical Hero Cases matching backend/app/database.py.
--   - Accused dossiers, custody records, FIRs, court cases, charges, and evidence.
--   - Intentional tamper test hash included for UTP-0012 remand order.
-- ══════════════════════════════════════════════════════════════════════════════

BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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
    updated_at          TIMESTAMPTZ DEFAULT NOW()
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
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Seed Organizations
INSERT INTO organizations (id, code, name, org_type, state, district)
VALUES 
    ('org_slsa_delhi', 'SLSA_DL', 'Delhi State Legal Services Authority', 'SLSA', 'Delhi', 'All (Statewide)'),
    ('org_dlsa_central', 'DLSA_CD', 'District Legal Services Authority, Central Delhi', 'DLSA', 'Delhi', 'Central Delhi'),
    ('org_dlsa_south', 'DLSA_SD', 'District Legal Services Authority, South Delhi', 'DLSA', 'Delhi', 'South Delhi'),
    ('org_tihar_jail', 'PRISON_TIHAR', 'Delhi Prisons Administration, Tihar Complex', 'PRISON', 'Delhi', 'West Delhi'),
    ('org_statutory_audit_delhi', 'AUDIT_DL', 'Statutory Judicial Audit Directorate', 'OVERSIGHT', 'Delhi', 'All (Statewide)')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, updated_at = NOW();

ALTER TABLE facilities ADD COLUMN IF NOT EXISTS state TEXT;
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS district TEXT;
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS capacity INT DEFAULT 500;
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS current_occupancy INT DEFAULT 0;

-- Seed Facilities
INSERT INTO facilities (id, organization_id, name, facility_type, state, district, capacity, current_occupancy)
VALUES 
    ('fac_tihar_jail_04', 'org_tihar_jail', 'Central Jail No. 4, Tihar (Synthetic)', 'CENTRAL_PRISON', 'Delhi', 'West Delhi', 1200, 1140),
    ('fac_tihar_jail_02', 'org_tihar_jail', 'Central Jail No. 2, Tihar (Synthetic)', 'CENTRAL_PRISON', 'Delhi', 'West Delhi', 1000, 920),
    ('fac_rohini_jail', 'org_tihar_jail', 'District Jail No. 2, Rohini (Synthetic)', 'DISTRICT_PRISON', 'Delhi', 'North West Delhi', 800, 780),
    ('fac_mandoli_jail', 'org_tihar_jail', 'Mandoli Jail Complex (Synthetic)', 'CENTRAL_PRISON', 'Delhi', 'East Delhi', 1500, 1310),
    ('fac_lucknow_jail', 'org_tihar_jail', 'Central Jail, Lucknow (Synthetic)', 'CENTRAL_PRISON', 'Uttar Pradesh', 'Lucknow', 2000, 1950),
    ('fac_bengaluru_jail', 'org_tihar_jail', 'Central Prison, Parappana Agrahara (Synthetic)', 'CENTRAL_PRISON', 'Karnataka', 'Bengaluru Urban', 2500, 2410)
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;


-- ── 2. RBAC LAYER: Organization Users (All 11 Roles) ─────────────────────────

CREATE TABLE IF NOT EXISTS organization_users (
    id                      TEXT PRIMARY KEY,
    organization_id         TEXT REFERENCES organizations(id) ON DELETE CASCADE,
    email                   TEXT UNIQUE NOT NULL,
    password_hash           TEXT,
    full_name               TEXT NOT NULL,
    role                    TEXT NOT NULL,
    phone                   TEXT,
    district                TEXT,
    state                   TEXT DEFAULT 'Delhi',
    facility_ids            JSONB DEFAULT '[]'::jsonb,
    police_station_id       TEXT,
    police_station          TEXT,
    jurisdiction_ids        JSONB DEFAULT '[]'::jsonb,
    authorized_district_ids JSONB DEFAULT '[]'::jsonb,
    linked_case_id          TEXT,
    relationship_to_accused TEXT,
    bar_registration_no     TEXT,
    specialization          TEXT,
    empanelment_category    TEXT,
    failed_login_count      INT DEFAULT 0,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Retrofit missing columns if organization_users already existed in database
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS state TEXT DEFAULT 'Delhi';
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS police_station_id TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS police_station TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS jurisdiction_ids JSONB DEFAULT '[]'::jsonb;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS authorized_district_ids JSONB DEFAULT '[]'::jsonb;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS specialization TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS empanelment_category TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS facility_ids JSONB DEFAULT '[]'::jsonb;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS linked_case_id TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS relationship_to_accused TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS bar_registration_no TEXT;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS failed_login_count INT DEFAULT 0;

-- Seed All 11 Demo Roles with authentic bcrypt hash for "Demo@12345"
INSERT INTO organization_users (
    id, organization_id, email, password_hash, full_name, role, phone, district, state,
    facility_ids, police_station_id, police_station, jurisdiction_ids, authorized_district_ids,
    linked_case_id, bar_registration_no, specialization, empanelment_category
)
VALUES
    (
        'demo_platform_admin', 'org_dlsa_central', 'admin@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'Platform Admin (Demo)', 'PLATFORM_ADMIN', '+91 98111 00001', 'Central Delhi', 'Delhi',
        '[]'::jsonb, NULL, NULL, '[]'::jsonb, '[]'::jsonb,
        NULL, NULL, NULL, NULL
    ),
    (
        'demo_gov_admin', 'org_slsa_delhi', 'govadmin@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'State Legal Services Oversight Officer (Demo)', 'GOV_ADMIN', '+91 98111 00002', 'All (Statewide)', 'Delhi',
        '[]'::jsonb, NULL, NULL, '[]'::jsonb, '["Central Delhi", "South Delhi", "West Delhi", "North Delhi", "East Delhi", "New Delhi", "Shahdara", "Rohini"]'::jsonb,
        NULL, NULL, NULL, NULL
    ),
    (
        'demo_jail_officer', 'org_tihar_jail', 'jail@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'Jail Officer (Demo)', 'JAIL_OFFICER', '+91 98111 00003', 'West Delhi', 'Delhi',
        '["fac_tihar_jail_04", "Central Jail No. 4, Tihar (Synthetic)", "Tihar"]'::jsonb, NULL, NULL, '[]'::jsonb, '[]'::jsonb,
        NULL, NULL, NULL, NULL
    ),
    (
        'demo_police_officer', 'org_dlsa_central', 'police@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'Police Officer (Demo)', 'POLICE_OFFICER', '+91 98111 00004', 'Central Delhi', 'Delhi',
        '[]'::jsonb, 'ps_kotwali_central', 'Kotwali Police Station', '["ps_kotwali_central", "Central Delhi"]'::jsonb, '[]'::jsonb,
        NULL, NULL, NULL, NULL
    ),
    (
        'demo_dlsa_officer', 'org_dlsa_central', 'dlsa@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'DLSA Officer (Demo)', 'DLSA_OFFICER', '+91 98111 00005', 'Central Delhi', 'Delhi',
        '[]'::jsonb, NULL, NULL, '[]'::jsonb, '[]'::jsonb,
        NULL, NULL, NULL, NULL
    ),
    (
        'demo_supervising', 'org_dlsa_central', 'supervisor@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'Supervising Legal Officer (Demo)', 'SUPERVISING_LEGAL_OFFICER', '+91 98111 00006', 'Central Delhi', 'Delhi',
        '[]'::jsonb, NULL, NULL, '[]'::jsonb, '[]'::jsonb,
        NULL, 'D/0842/2012', 'Judicial Oversight & Human Rights', 'Supervising Officer'
    ),
    (
        'demo_advocate', 'org_dlsa_central', 'advocate@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'Defense Advocate (Demo)', 'DEFENSE_ADVOCATE', '+91 98111 00007', 'Central Delhi', 'Delhi',
        '[]'::jsonb, NULL, NULL, '[]'::jsonb, '[]'::jsonb,
        'UTP-0001', 'D/1420/2018', 'Undertrial Defense & Bail', 'DLSA Senior Panel Counsel'
    ),
    (
        'demo_ext_advocate', 'org_dlsa_central', 'extadvocate@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'External Advocate (Demo)', 'CONTROLLED_EXTERNAL_ADVOCATE', '+91 98111 00008', 'Central Delhi', 'Delhi',
        '[]'::jsonb, NULL, NULL, '[]'::jsonb, '[]'::jsonb,
        'UTP-0001', 'D/2984/2021', 'Criminal Defense', 'Panel Advocate'
    ),
    (
        'demo_accused', 'org_dlsa_central', 'accused@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'Accused Person (Demo)', 'ACCUSED_USER', '+91 98111 00009', 'Central Delhi', 'Delhi',
        '[]'::jsonb, NULL, NULL, '[]'::jsonb, '[]'::jsonb,
        'UTP-0001', NULL, NULL, NULL
    ),
    (
        'demo_family', 'org_dlsa_central', 'family@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'Family Guardian (Demo)', 'FAMILY_GUARDIAN', '+91 98111 00010', 'Central Delhi', 'Delhi',
        '[]'::jsonb, NULL, NULL, '[]'::jsonb, '[]'::jsonb,
        'UTP-0007', NULL, NULL, NULL
    ),
    (
        'demo_auditor', 'org_statutory_audit_delhi', 'auditor@demo.nyayamitra.in',
        '$2b$12$NanP2rDHTN3OrKV0MYcGzeBvcaILPUvWeH9VwjEmhRcIUjejLcRq2',
        'Statutory Oversight Auditor (Demo)', 'READ_ONLY_AUDITOR', '+91 98111 00011', 'All (Statewide)', 'Delhi',
        '[]'::jsonb, NULL, NULL, '[]'::jsonb, '["Central Delhi", "South Delhi", "West Delhi", "North Delhi", "East Delhi", "New Delhi", "Shahdara", "Rohini"]'::jsonb,
        NULL, NULL, NULL, NULL
    )
ON CONFLICT (id) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    facility_ids = EXCLUDED.facility_ids,
    police_station_id = EXCLUDED.police_station_id,
    authorized_district_ids = EXCLUDED.authorized_district_ids,
    linked_case_id = EXCLUDED.linked_case_id,
    updated_at = NOW();


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
    source_system           TEXT DEFAULT 'Nyaya Mitra Case Index',
    source_record_id        TEXT,
    data_source_status      TEXT DEFAULT 'DEMO_SYNTHETIC',
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Retrofit missing columns if accused_persons already existed in database
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS source_system TEXT DEFAULT 'Nyaya Mitra Case Index';
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS source_record_id TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS gender TEXT DEFAULT 'Male';
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS age INT DEFAULT 30;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS preferred_language TEXT DEFAULT 'en';
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS health_vulnerability BOOLEAN DEFAULT FALSE;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS health_details TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS is_senior_citizen BOOLEAN DEFAULT FALSE;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS repeat_offender BOOLEAN DEFAULT FALSE;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS relative_name TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS relative_relation TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS relative_phone TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS permanent_address TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS data_source_status TEXT DEFAULT 'DEMO_SYNTHETIC';

INSERT INTO accused_persons (
    id, full_name, gender, age, preferred_language, health_vulnerability, health_details,
    is_senior_citizen, repeat_offender, relative_name, relative_relation, relative_phone,
    permanent_address, source_record_id, data_source_status
)
VALUES
    ('acc_utp_0001', 'Suresh Patel', 'Male', 28, 'en', FALSE, NULL, FALSE, FALSE, 'Ramesh Kumar', 'Father', '+91 98765 11001', 'Plot 42, Gandhi Nagar, Sector 4, Chennai, TN - 600001', 'UTP-0001', 'DEMO_SYNTHETIC'),
    ('acc_utp_0007', 'Ramesh Kumar', 'Male', 63, 'hi', TRUE, 'Chronic hypertension and joint arthritis under prison dispensary care.', TRUE, FALSE, 'Sunita Devi', 'Spouse / Wife', '+91 98765 77007', 'Flat 12B, Old City Suburb, Jaipur, RJ - 302001', 'UTP-0007', 'DEMO_SYNTHETIC'),
    ('acc_utp_0015', 'Anand Singh', 'Male', 40, 'hi', FALSE, NULL, FALSE, TRUE, 'Raghuvir Singh', 'Brother', '+91 98765 15015', 'Village Rampur, Post Office Sub-Jail Zone, Lucknow, UP - 226001', 'UTP-0015', 'DEMO_SYNTHETIC'),
    ('acc_utp_0012', 'Mohd. Ahmed', 'Male', 34, 'kn', FALSE, NULL, FALSE, TRUE, 'Fatima Bi', 'Sister', '+91 98765 12012', 'House 88, Shivaji Road, Bengaluru, KA - 560002', 'UTP-0012', 'DEMO_SYNTHETIC'),
    ('acc_conv_0101', 'Vikramaditya Rao', 'Male', 42, 'hi', FALSE, NULL, FALSE, FALSE, 'Meena Rao', 'Spouse', '+91 98765 33001', 'H.No 12, Saket Sector 3, New Delhi - 110017', 'CONV-0101', 'DEMO_SYNTHETIC'),
    ('acc_rel_0042', 'Deepak Verma', 'Male', 38, 'hi', FALSE, NULL, FALSE, FALSE, 'Pooja Verma', 'Spouse', '+91 98765 44002', 'H.No 44, Civil Lines, Delhi - 110054', 'REL-0042', 'DEMO_SYNTHETIC')
ON CONFLICT (id) DO UPDATE SET
    full_name = EXCLUDED.full_name,
    health_vulnerability = EXCLUDED.health_vulnerability,
    health_details = EXCLUDED.health_details,
    updated_at = NOW();

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
);

-- Retrofit missing columns if custody_records already existed in database
ALTER TABLE custody_records ADD COLUMN IF NOT EXISTS prisoner_category TEXT DEFAULT 'UNDERTRIAL';
ALTER TABLE custody_records ADD COLUMN IF NOT EXISTS calendar_custody_days INT DEFAULT 0;
ALTER TABLE custody_records ADD COLUMN IF NOT EXISTS excluded_delay_days INT DEFAULT 0;
ALTER TABLE custody_records ADD COLUMN IF NOT EXISTS countable_custody_days INT DEFAULT 0;
ALTER TABLE custody_records ADD COLUMN IF NOT EXISTS is_current_custody BOOLEAN DEFAULT TRUE;
ALTER TABLE custody_records ADD COLUMN IF NOT EXISTS release_date DATE;

INSERT INTO custody_records (id, accused_id, facility_id, admission_date, prisoner_category, calendar_custody_days, excluded_delay_days, countable_custody_days, is_current_custody, release_date)
VALUES 
    ('cus_utp_0001', 'acc_utp_0001', 'fac_tihar_jail_04', '2025-01-10', 'UNDERTRIAL', 200, 0, 200, TRUE, NULL),
    ('cus_utp_0007', 'acc_utp_0007', 'fac_rohini_jail',    '2024-11-02', 'UNDERTRIAL', 410, 0, 410, TRUE, NULL),
    ('cus_utp_0015', 'acc_utp_0015', 'fac_lucknow_jail',  '2023-03-01', 'UNDERTRIAL', 850, 0, 850, TRUE, NULL),
    ('cus_utp_0012', 'acc_utp_0012', 'fac_bengaluru_jail','2023-06-15', 'UNDERTRIAL', 400, 45, 355, TRUE, NULL),
    ('cus_conv_0101', 'acc_conv_0101', 'fac_tihar_jail_02', '2024-02-15', 'CONVICTED',  560, 0, 560, TRUE, NULL),
    ('cus_rel_0042', 'acc_rel_0042', 'fac_tihar_jail_04', '2024-06-20', 'UNDERTRIAL', 320, 0, 320, FALSE, '2025-05-06')
ON CONFLICT (id) DO UPDATE SET
    calendar_custody_days = EXCLUDED.calendar_custody_days,
    countable_custody_days = EXCLUDED.countable_custody_days,
    updated_at = NOW();


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

INSERT INTO firs (id, fir_number, police_station, district, state, filing_date)
VALUES 
    ('fir_utp_0001', 'FIR-2025-010', 'Kotwali Police Station', 'Central Delhi', 'Delhi', '2025-01-10'),
    ('fir_utp_0007', 'FIR-2024-412', 'Old City Suburb Police Station', 'South Delhi', 'Delhi', '2024-11-02'),
    ('fir_utp_0015', 'FIR-2023-108', 'Rampur Police Station', 'Lucknow', 'Uttar Pradesh', '2023-03-01'),
    ('fir_utp_0012', 'FIR-2023-551', 'Shivaji Road Police Station', 'Bengaluru Urban', 'Karnataka', '2023-06-15'),
    ('fir_conv_0101', 'FIR-2024-119', 'Saket Police Station', 'South Delhi', 'Delhi', '2024-02-15'),
    ('fir_rel_0042', 'FIR-2024-220', 'Civil Lines Police Station', 'Central Delhi', 'Delhi', '2024-06-20')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS court_cases (
    id                      TEXT PRIMARY KEY,
    case_number             TEXT NOT NULL,
    accused_id              TEXT NOT NULL REFERENCES accused_persons(id) ON DELETE CASCADE,
    fir_id                  TEXT REFERENCES firs(id),
    organization_id         TEXT REFERENCES organizations(id),
    cnr_number              TEXT,
    court_name              TEXT NOT NULL,
    district                TEXT,
    state                   TEXT,
    legal_code              TEXT DEFAULT 'BNS_2023',
    current_status          TEXT DEFAULT 'DETECTED',
    dlsa_reference_number   TEXT,
    assigned_lawyer_id      TEXT,
    assignment_status       TEXT DEFAULT 'AVAILABLE',
    data_source_status      TEXT DEFAULT 'DEMO_SYNTHETIC',
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Retrofit missing columns if court_cases already existed in database
ALTER TABLE court_cases ADD COLUMN IF NOT EXISTS dlsa_reference_number TEXT;
ALTER TABLE court_cases ADD COLUMN IF NOT EXISTS assigned_lawyer_id TEXT;
ALTER TABLE court_cases ADD COLUMN IF NOT EXISTS assignment_status TEXT DEFAULT 'AVAILABLE';
ALTER TABLE court_cases ADD COLUMN IF NOT EXISTS data_source_status TEXT DEFAULT 'DEMO_SYNTHETIC';

INSERT INTO court_cases (
    id, case_number, accused_id, fir_id, organization_id, cnr_number, court_name,
    district, state, legal_code, current_status, dlsa_reference_number,
    assigned_lawyer_id, assignment_status, data_source_status
)
VALUES 
    ('UTP-0001', 'UTP-0001', 'acc_utp_0001', 'fir_utp_0001', 'org_dlsa_central', 'DLCT010049212025', 'Metropolitan Magistrate Court 02, Central', 'Central Delhi', 'Delhi', 'BNS_2023', 'ELIGIBLE', 'DLSA-CD-2025-0112', 'demo_advocate', 'ASSIGNED', 'DEMO_SYNTHETIC'),
    ('UTP-0007', 'UTP-0007', 'acc_utp_0007', 'fir_utp_0007', 'org_dlsa_south',   'DLST020088122024', 'Additional Chief Judicial Magistrate, South', 'South Delhi', 'Delhi', 'BNS_2023', 'ELIGIBLE', 'DLSA-SD-2024-887', NULL, 'AVAILABLE', 'DEMO_SYNTHETIC'),
    ('UTP-0015', 'UTP-0015', 'acc_utp_0015', 'fir_utp_0015', 'org_dlsa_central', 'UPCZ010091212023', 'Chief Judicial Magistrate, Lucknow', 'Lucknow', 'Uttar Pradesh', 'IPC_1860', 'DOCUMENTS_MISSING', 'DLSA-LK-2023-304', NULL, 'AVAILABLE', 'DEMO_SYNTHETIC'),
    ('UTP-0012', 'UTP-0012', 'acc_utp_0012', 'fir_utp_0012', 'org_dlsa_central', 'KABC010077412023', 'Principal Sessions Judge, Bengaluru', 'Bengaluru Urban', 'Karnataka', 'IPC_1860', 'MANUAL_REVIEW', 'DLSA-BNG-2023-902', NULL, 'AVAILABLE', 'DEMO_SYNTHETIC'),
    ('CONV-0101', 'CONV-0101', 'acc_conv_0101', 'fir_conv_0101', 'org_dlsa_south', 'DLST010033192024', 'Court of Sessions, Saket', 'South Delhi', 'Delhi', 'BNS_2023', 'APPEAL_PENDING', 'DLSA-SD-2024-CONV-012', NULL, 'AVAILABLE', 'DEMO_SYNTHETIC'),
    ('REL-0042', 'REL-0042', 'acc_rel_0042', 'fir_rel_0042', 'org_dlsa_central', 'DLCT020055192024', 'Chief Metropolitan Magistrate, Central', 'Central Delhi', 'Delhi', 'IPC_1860', 'POST_RELEASE_PRESERVED', 'DLSA-CD-2024-512', 'Legal Officer 104', 'ASSIGNED', 'DEMO_SYNTHETIC')
ON CONFLICT (id) DO UPDATE SET
    current_status = EXCLUDED.current_status,
    assigned_lawyer_id = EXCLUDED.assigned_lawyer_id,
    assignment_status = EXCLUDED.assignment_status,
    updated_at = NOW();

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

INSERT INTO charges (id, case_id, legal_code, section_number, offence_title, max_imprisonment_days, is_capital_offence)
VALUES 
    ('chg_utp_0001_bns_115', 'UTP-0001', 'BNS_2023', 'BNS 115(2)', 'Voluntarily causing hurt', 365, FALSE),
    ('chg_utp_0007_bns_303', 'UTP-0007', 'BNS_2023', 'BNS 303(2)', 'Theft in dwelling house', 730, FALSE),
    ('chg_utp_0015_ipc_392', 'UTP-0015', 'IPC_1860', 'IPC 392', 'Robbery', 1095, FALSE),
    ('chg_utp_0012_ipc_302', 'UTP-0012', 'IPC_1860', 'IPC 302', 'Murder (Capital Offence)', 18250, TRUE),
    ('chg_conv_0101_bns_105', 'CONV-0101', 'BNS_2023', 'BNS 105', 'Culpable homicide not amounting to murder', 3650, FALSE),
    ('chg_rel_0042_ipc_420', 'REL-0042', 'IPC_1860', 'IPC 420', 'Cheating and dishonestly inducing delivery of property', 730, FALSE)
ON CONFLICT (id) DO NOTHING;


-- ── 5. EVIDENCE & DOCUMENTS: Vault, Hashes & Tamper Demos ────────────────────

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id         TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    document_type       TEXT NOT NULL,
    file_name           TEXT NOT NULL,
    stored_hash         TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO evidence (evidence_id, case_id, document_type, file_name, stored_hash, created_at)
VALUES 
    ('EVI-UTP-0001-remand_order', 'UTP-0001', 'remand_order', 'remand_order.pdf', encode(digest('verified_content_UTP-0001_remand_order', 'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0001-charge_sheet', 'UTP-0001', 'charge_sheet', 'charge_sheet.pdf', encode(digest('verified_content_UTP-0001_charge_sheet', 'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0007-remand_order', 'UTP-0007', 'remand_order', 'remand_order.pdf', encode(digest('verified_content_UTP-0007_remand_order', 'sha256'), 'hex'), NOW()),
    ('EVI-UTP-0007-charge_sheet', 'UTP-0007', 'charge_sheet', 'charge_sheet.pdf', encode(digest('verified_content_UTP-0007_charge_sheet', 'sha256'), 'hex'), NOW()),
    -- Deliberate mismatch on UTP-0012 for evidentiary tamper detection testing
    ('EVI-UTP-0012-remand_order', 'UTP-0012', 'remand_order', 'remand_order.pdf', 'deadbeef' || substr(encode(digest('verified_content_UTP-0012_remand_order', 'sha256'), 'hex'), 9), NOW()),
    ('EVI-UTP-0015-remand_order', 'UTP-0015', 'remand_order', 'remand_order.pdf', encode(digest('verified_content_UTP-0015_remand_order', 'sha256'), 'hex'), NOW()),
    ('EVI-CONV-0101-judgment',   'CONV-0101', 'trial_court_judgment', 'judgment.pdf', encode(digest('verified_content_CONV-0101_judgment', 'sha256'), 'hex'), NOW()),
    ('EVI-REL-0042-release_memo', 'REL-0042', 'release_memo', 'release_memo.pdf', encode(digest('verified_content_REL-0042_release_memo', 'sha256'), 'hex'), NOW())
ON CONFLICT (evidence_id) DO UPDATE SET stored_hash = EXCLUDED.stored_hash;

CREATE TABLE IF NOT EXISTS documents (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    document_type       TEXT NOT NULL,
    file_name           TEXT,
    storage_path        TEXT,
    file_size_bytes     INT DEFAULT 0,
    mime_type           TEXT DEFAULT 'application/pdf',
    sha256_hash         TEXT,
    is_mandatory        BOOLEAN DEFAULT TRUE,
    is_present          BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Retrofit missing columns if documents already existed in database
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_name TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size_bytes INT DEFAULT 0;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type TEXT DEFAULT 'application/pdf';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS sha256_hash TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_mandatory BOOLEAN DEFAULT TRUE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_present BOOLEAN DEFAULT TRUE;

INSERT INTO documents (id, case_id, document_type, file_name, storage_path, file_size_bytes, mime_type, sha256_hash, is_mandatory, is_present)
VALUES 
    ('doc_utp_0001_remand', 'UTP-0001', 'remand_order', 'remand_order.pdf', '/vault/UTP-0001/remand_order.pdf', 1048576, 'application/pdf', encode(digest('verified_content_UTP-0001_remand_order', 'sha256'), 'hex'), TRUE, TRUE),
    ('doc_utp_0001_charge', 'UTP-0001', 'charge_sheet', 'charge_sheet.pdf', '/vault/UTP-0001/charge_sheet.pdf', 2097152, 'application/pdf', encode(digest('verified_content_UTP-0001_charge_sheet', 'sha256'), 'hex'), TRUE, TRUE),
    ('doc_utp_0007_remand', 'UTP-0007', 'remand_order', 'remand_order.pdf', '/vault/UTP-0007/remand_order.pdf', 1048576, 'application/pdf', encode(digest('verified_content_UTP-0007_remand_order', 'sha256'), 'hex'), TRUE, TRUE),
    ('doc_utp_0007_charge', 'UTP-0007', 'charge_sheet', 'charge_sheet.pdf', '/vault/UTP-0007/charge_sheet.pdf', 2097152, 'application/pdf', encode(digest('verified_content_UTP-0007_charge_sheet', 'sha256'), 'hex'), TRUE, TRUE)
ON CONFLICT (id) DO NOTHING;


-- ── 6. UNIFIED JSON CASES TABLE (BACKWARD COMPATIBILITY) ──────────────────────

CREATE TABLE IF NOT EXISTS cases (
    case_id             TEXT PRIMARY KEY,
    data                JSONB NOT NULL,
    status              TEXT DEFAULT 'DETECTED',
    assignment_status   TEXT DEFAULT 'AVAILABLE',
    assigned_lawyer_id  TEXT,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Retrofit missing columns if cases already existed in database
ALTER TABLE cases ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'DETECTED';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS assignment_status TEXT DEFAULT 'AVAILABLE';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS assigned_lawyer_id TEXT;

INSERT INTO cases (case_id, data, status, assignment_status, assigned_lawyer_id)
VALUES
    (
        'UTP-0001',
        jsonb_build_object(
            'case_id', 'UTP-0001',
            'name', 'Suresh Patel (Synthetic)',
            'prisoner_category', 'UNDERTRIAL',
            'legal_code', 'BNS_2023',
            'offense_sections', jsonb_build_array('BNS 115(2)'),
            'cnr_number', 'DLCT010049212025',
            'fir_number', 'FIR-2025-010',
            'police_station', 'Kotwali Police Station',
            'police_station_id', 'ps_kotwali_central',
            'court_name', 'Metropolitan Magistrate Court 02, Central',
            'district', 'Central Delhi',
            'state', 'Delhi',
            'dlsa_reference_number', 'DLSA-CD-2025-0112',
            'arrest_date', '2025-01-10',
            'custody_days', 200,
            'excluded_delay_days', 0,
            'max_sentence_days_for_offense', 365,
            'punishable_by_death_or_life', false,
            'multiple_active_cases', false,
            'required_docs', jsonb_build_array('remand_order', 'charge_sheet'),
            'present_docs', jsonb_build_array('remand_order', 'charge_sheet'),
            'urgency_flags', jsonb_build_object('age', 28, 'health_flag', false, 'repeat_offender', false),
            'jail_location', 'Central Jail No. 4, Tihar (Synthetic)',
            'preferred_language', 'en',
            'relative_name', 'Ramesh Kumar (Synthetic)',
            'relative_relation', 'Father',
            'relative_phone', '+91 98765 11001',
            'permanent_address', 'Plot 42, Gandhi Nagar, Sector 4, Chennai, TN - 600001',
            'assignment_status', 'ASSIGNED',
            'assigned_lawyer_id', 'demo_advocate',
            'assigned_lawyer', 'Adv. Rajesh Sharma (Demo)',
            'status', 'ELIGIBLE'
        ),
        'ELIGIBLE', 'ASSIGNED', 'demo_advocate'
    ),
    (
        'UTP-0007',
        jsonb_build_object(
            'case_id', 'UTP-0007',
            'name', 'Ramesh Kumar (Synthetic)',
            'prisoner_category', 'UNDERTRIAL',
            'legal_code', 'BNS_2023',
            'offense_sections', jsonb_build_array('BNS 303(2)'),
            'cnr_number', 'DLST020088122024',
            'fir_number', 'FIR-2024-412',
            'police_station', 'Old City Suburb Police Station',
            'police_station_id', 'ps_old_city',
            'court_name', 'Additional Chief Judicial Magistrate, South',
            'district', 'South Delhi',
            'state', 'Delhi',
            'dlsa_reference_number', 'DLSA-SD-2024-887',
            'arrest_date', '2024-11-02',
            'custody_days', 410,
            'excluded_delay_days', 0,
            'max_sentence_days_for_offense', 730,
            'punishable_by_death_or_life', false,
            'multiple_active_cases', false,
            'required_docs', jsonb_build_array('remand_order', 'charge_sheet'),
            'present_docs', jsonb_build_array('remand_order', 'charge_sheet'),
            'urgency_flags', jsonb_build_object('age', 63, 'health_flag', true, 'health_details', 'Chronic hypertension and joint arthritis under prison dispensary care.', 'repeat_offender', false),
            'jail_location', 'District Jail No. 2, Rohini (Synthetic)',
            'preferred_language', 'hi',
            'relative_name', 'Sunita Devi (Synthetic)',
            'relative_relation', 'Spouse / Wife',
            'relative_phone', '+91 98765 77007',
            'permanent_address', 'Flat 12B, Old City Suburb, Jaipur, RJ - 302001',
            'assignment_status', 'AVAILABLE',
            'status', 'ELIGIBLE'
        ),
        'ELIGIBLE', 'AVAILABLE', NULL
    ),
    (
        'UTP-0015',
        jsonb_build_object(
            'case_id', 'UTP-0015',
            'name', 'Anand Singh (Synthetic)',
            'prisoner_category', 'UNDERTRIAL',
            'legal_code', 'IPC_1860',
            'offense_sections', jsonb_build_array('IPC 392'),
            'cnr_number', 'UPCZ010091212023',
            'fir_number', 'FIR-2023-108',
            'police_station', 'Rampur Police Station',
            'police_station_id', 'ps_rampur',
            'court_name', 'Chief Judicial Magistrate, Lucknow',
            'district', 'Lucknow',
            'state', 'Uttar Pradesh',
            'dlsa_reference_number', 'DLSA-LK-2023-304',
            'arrest_date', '2023-03-01',
            'custody_days', 850,
            'excluded_delay_days', 0,
            'max_sentence_days_for_offense', 1095,
            'punishable_by_death_or_life', false,
            'multiple_active_cases', false,
            'required_docs', jsonb_build_array('remand_order', 'charge_sheet'),
            'present_docs', jsonb_build_array('remand_order'),
            'urgency_flags', jsonb_build_object('age', 40, 'health_flag', false, 'repeat_offender', true),
            'jail_location', 'Central Jail, Lucknow (Synthetic)',
            'preferred_language', 'hi',
            'relative_name', 'Raghuvir Singh (Synthetic)',
            'relative_relation', 'Brother',
            'relative_phone', '+91 98765 15015',
            'permanent_address', 'Village Rampur, Post Office Sub-Jail Zone, Lucknow, UP - 226001',
            'assignment_status', 'AVAILABLE',
            'status', 'DOCUMENTS_MISSING'
        ),
        'DOCUMENTS_MISSING', 'AVAILABLE', NULL
    ),
    (
        'UTP-0012',
        jsonb_build_object(
            'case_id', 'UTP-0012',
            'name', 'Mohd. Ahmed (Synthetic)',
            'prisoner_category', 'UNDERTRIAL',
            'legal_code', 'IPC_1860',
            'offense_sections', jsonb_build_array('IPC 302'),
            'cnr_number', 'KABC010077412023',
            'fir_number', 'FIR-2023-551',
            'police_station', 'Shivaji Road Police Station',
            'police_station_id', 'ps_shivaji_rd',
            'court_name', 'Principal Sessions Judge, Bengaluru',
            'district', 'Bengaluru Urban',
            'state', 'Karnataka',
            'dlsa_reference_number', 'DLSA-BNG-2023-902',
            'arrest_date', '2023-06-15',
            'custody_days', 400,
            'excluded_delay_days', 45,
            'max_sentence_days_for_offense', 18250,
            'punishable_by_death_or_life', true,
            'multiple_active_cases', true,
            'required_docs', jsonb_build_array('remand_order', 'charge_sheet'),
            'present_docs', jsonb_build_array('remand_order', 'charge_sheet'),
            'urgency_flags', jsonb_build_object('age', 34, 'health_flag', false, 'repeat_offender', true),
            'jail_location', 'Central Prison, Parappana Agrahara (Synthetic)',
            'preferred_language', 'kn',
            'relative_name', 'Fatima Bi (Synthetic)',
            'relative_relation', 'Sister',
            'relative_phone', '+91 98765 12012',
            'permanent_address', 'House 88, Shivaji Road, Bengaluru, KA - 560002',
            'assignment_status', 'AVAILABLE',
            'status', 'MANUAL_REVIEW'
        ),
        'MANUAL_REVIEW', 'AVAILABLE', NULL
    ),
    (
        'CONV-0101',
        jsonb_build_object(
            'case_id', 'CONV-0101',
            'name', 'Vikramaditya Rao (Synthetic)',
            'prisoner_category', 'CONVICTED',
            'legal_code', 'BNS_2023',
            'offense_sections', jsonb_build_array('BNS 105'),
            'cnr_number', 'DLST010033192024',
            'fir_number', 'FIR-2024-119',
            'police_station', 'Saket Police Station',
            'police_station_id', 'ps_saket',
            'court_name', 'Court of Sessions, Saket',
            'district', 'South Delhi',
            'state', 'Delhi',
            'dlsa_reference_number', 'DLSA-SD-2024-CONV-012',
            'arrest_date', '2024-02-15',
            'custody_days', 560,
            'excluded_delay_days', 0,
            'max_sentence_days_for_offense', 3650,
            'punishable_by_death_or_life', false,
            'multiple_active_cases', false,
            'required_docs', jsonb_build_array('trial_court_judgment', 'custody_certificate', 'nominal_roll'),
            'present_docs', jsonb_build_array('trial_court_judgment', 'custody_certificate'),
            'urgency_flags', jsonb_build_object('age', 42, 'health_flag', false, 'repeat_offender', false),
            'jail_location', 'Central Jail No. 2, Tihar (Synthetic)',
            'preferred_language', 'hi',
            'relative_name', 'Meena Rao (Synthetic)',
            'relative_relation', 'Spouse',
            'relative_phone', '+91 98765 33001',
            'permanent_address', 'H.No 12, Saket Sector 3, New Delhi - 110017',
            'assignment_status', 'AVAILABLE',
            'status', 'APPEAL_PENDING'
        ),
        'APPEAL_PENDING', 'AVAILABLE', NULL
    ),
    (
        'REL-0042',
        jsonb_build_object(
            'case_id', 'REL-0042',
            'name', 'Deepak Verma (Synthetic)',
            'prisoner_category', 'UNDERTRIAL',
            'legal_code', 'IPC_1860',
            'offense_sections', jsonb_build_array('IPC 420'),
            'cnr_number', 'DLCT020055192024',
            'fir_number', 'FIR-2024-220',
            'police_station', 'Civil Lines Police Station',
            'police_station_id', 'ps_civil_lines',
            'court_name', 'Chief Metropolitan Magistrate, Central',
            'district', 'Central Delhi',
            'state', 'Delhi',
            'dlsa_reference_number', 'DLSA-CD-2024-512',
            'arrest_date', '2024-06-20',
            'custody_days', 320,
            'excluded_delay_days', 0,
            'max_sentence_days_for_offense', 730,
            'punishable_by_death_or_life', false,
            'multiple_active_cases', false,
            'required_docs', jsonb_build_array('remand_order', 'charge_sheet', 'bail_order', 'release_memo'),
            'present_docs', jsonb_build_array('remand_order', 'charge_sheet', 'bail_order', 'release_memo'),
            'urgency_flags', jsonb_build_object('age', 38, 'health_flag', false, 'repeat_offender', false),
            'jail_location', 'Central Jail No. 4, Tihar (Synthetic)',
            'preferred_language', 'hi',
            'relative_name', 'Pooja Verma (Synthetic)',
            'relative_relation', 'Spouse',
            'relative_phone', '+91 98765 44002',
            'permanent_address', 'H.No 44, Civil Lines, Delhi - 110054',
            'assignment_status', 'ASSIGNED',
            'assigned_lawyer_id', 'Legal Officer 104',
            'status', 'POST_RELEASE_PRESERVED'
        ),
        'POST_RELEASE_PRESERVED', 'ASSIGNED', 'Legal Officer 104'
    )
ON CONFLICT (case_id) DO UPDATE SET
    data = EXCLUDED.data,
    status = EXCLUDED.status,
    assignment_status = EXCLUDED.assignment_status,
    assigned_lawyer_id = EXCLUDED.assigned_lawyer_id,
    updated_at = NOW();

COMMIT;

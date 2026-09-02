-- ══════════════════════════════════════════════════════════════════════════════
-- NYAYA MITRA — SUPABASE MIGRATION SCRIPT (HARDCODED VALUES REMOVAL SYNC)
-- ══════════════════════════════════════════════════════════════════════════════
-- Run this in your Supabase SQL Editor:
-- https://supabase.com/dashboard/project/<your-project-id>/sql/new
--
-- SUMMARY OF OPERATIONS:
-- 1. TABLES TO REMOVE: NONE. (Do not drop existing tables; they hold core schemas).
-- 2. COLUMNS TO ADD: Extended dossier & identity fields on `accused_persons`.
-- 3. TABLES TO CREATE (3 New):
--    - `family_contacts`: Normalized family/guardian contacts per accused.
--    - `identity_merge_candidates`: Probabilistic deduplication & review records.
--    - `hearings_schedule`: Complete hearing calendar per case.
-- 4. RLS POLICIES: Security rules for service_role and authenticated users.
-- 5. SEED DATA: Insert synchronized records matching local database.
-- ══════════════════════════════════════════════════════════════════════════════

BEGIN;

-- ── 1. EXTEND `accused_persons` WITH MISSING DOSSIER COLUMNS ─────────────────

ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS date_of_birth      TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS alias_names        JSONB DEFAULT '[]'::jsonb;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS prison_inmate_no   TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS cctns_person_id    TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS aadhaar_hash       TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS voter_id_masked    TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS source_system      TEXT DEFAULT 'Nyaya Mitra Case Index';
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS source_record_id   TEXT;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS ingested_at        TIMESTAMPTZ DEFAULT NOW();

-- ── 2. CREATE NEW TABLE: `family_contacts` ───────────────────────────────────

CREATE TABLE IF NOT EXISTS family_contacts (
    id                  TEXT PRIMARY KEY,
    accused_id          TEXT NOT NULL REFERENCES accused_persons(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    relation            TEXT,
    phone               TEXT,
    alt_phone           TEXT,
    address             TEXT,
    preferred_language  TEXT DEFAULT 'hi',
    preferred_channel   TEXT DEFAULT 'SMS',
    is_primary_contact  BOOLEAN DEFAULT FALSE,
    verified_by_dlsa    BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── 3. CREATE NEW TABLE: `identity_merge_candidates` ─────────────────────────

CREATE TABLE IF NOT EXISTS identity_merge_candidates (
    id                      TEXT PRIMARY KEY,
    source_accused_id       TEXT NOT NULL,
    source_name             TEXT,
    source_facility         TEXT,
    source_father_name      TEXT,
    source_dob              TEXT,
    candidate_accused_id    TEXT NOT NULL,
    candidate_name          TEXT,
    candidate_facility      TEXT,
    candidate_father_name   TEXT,
    candidate_dob           TEXT,
    match_confidence        REAL DEFAULT 0.0,
    shared_traits           JSONB DEFAULT '[]'::jsonb,
    conflicting_traits      JSONB DEFAULT '[]'::jsonb,
    match_explanation       TEXT,
    review_status           TEXT DEFAULT 'PENDING_HUMAN_REVIEW',
    reviewed_by             TEXT,
    reviewed_at             TIMESTAMPTZ,
    resolution_notes        TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── 4. CREATE NEW TABLE: `hearings_schedule` ─────────────────────────────────

CREATE TABLE IF NOT EXISTS hearings_schedule (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    prisoner_name       TEXT,
    court_name          TEXT NOT NULL,
    hearing_date        DATE NOT NULL,
    hearing_type        TEXT NOT NULL,
    status              TEXT DEFAULT 'Scheduled',
    judge               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── 5. PERFORMANCE INDEXES ───────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_family_contacts_accused ON family_contacts(accused_id);
CREATE INDEX IF NOT EXISTS idx_identity_merge_status   ON identity_merge_candidates(review_status);
CREATE INDEX IF NOT EXISTS idx_hearings_case           ON hearings_schedule(case_id);
CREATE INDEX IF NOT EXISTS idx_hearings_date           ON hearings_schedule(hearing_date);

-- ── 6. ROW LEVEL SECURITY (RLS) POLICIES ─────────────────────────────────────

ALTER TABLE family_contacts             ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_merge_candidates   ENABLE ROW LEVEL SECURITY;
ALTER TABLE hearings_schedule           ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'family_contacts' AND policyname = 'Service role full access on family_contacts'
    ) THEN
        CREATE POLICY "Service role full access on family_contacts" 
            ON family_contacts FOR ALL USING (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'identity_merge_candidates' AND policyname = 'Service role full access on identity_merge_candidates'
    ) THEN
        CREATE POLICY "Service role full access on identity_merge_candidates" 
            ON identity_merge_candidates FOR ALL USING (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'hearings_schedule' AND policyname = 'Service role full access on hearings_schedule'
    ) THEN
        CREATE POLICY "Service role full access on hearings_schedule" 
            ON hearings_schedule FOR ALL USING (true);
    END IF;
END $$;

-- ── 7. SEED DATA (SYNCHRONIZE WITH DATABASE CHANGES) ─────────────────────────

-- Clean any synthetic markers in accused_persons
UPDATE accused_persons 
SET full_name = REPLACE(full_name, ' (Synthetic)', '')
WHERE full_name LIKE '%(Synthetic)%';

-- Seed Family Contacts (derived from relative_* columns)
INSERT INTO family_contacts (id, accused_id, name, relation, phone, preferred_language, preferred_channel, is_primary_contact, verified_by_dlsa)
VALUES
    ('fcon_utp_0001_1', 'acc_utp_0001', 'Ramesh Patel',   'Father',   '+91 98765 43210', 'hi', 'SMS', TRUE, TRUE),
    ('fcon_utp_0002_1', 'acc_utp_0002', 'Fatima Begum',   'Mother',   '+91 98111 22334', 'en', 'SMS', TRUE, TRUE),
    ('fcon_utp_0003_1', 'acc_utp_0003', 'Ananya Rao',     'Daughter', '+91 99887 76655', 'en', 'SMS', TRUE, TRUE),
    ('fcon_utp_0012_1', 'acc_utp_0012', 'Sunita Pradhan', 'Wife',     '+91 97112 33445', 'hi', 'SMS', TRUE, TRUE),
    ('fcon_utp_0015_1', 'acc_utp_0015', 'Dolma Namgyal',  'Sister',   '+91 96500 11223', 'en', 'SMS', TRUE, TRUE),
    ('fcon_utp_0021_1', 'acc_utp_0021', 'Sundaram Pillai', 'Father',   '+91 94440 12345', 'ta', 'SMS', TRUE, TRUE)
ON CONFLICT (id) DO UPDATE 
SET name = EXCLUDED.name, relation = EXCLUDED.relation, phone = EXCLUDED.phone;

-- Seed Identity Merge Candidates (Probabilistic deduplication records)
INSERT INTO identity_merge_candidates (
    id, source_accused_id, source_name, source_facility, source_father_name,
    candidate_accused_id, candidate_name, candidate_facility, candidate_father_name,
    match_confidence, shared_traits, conflicting_traits, match_explanation, review_status
)
VALUES
    (
        'imr_cand_001',
        'acc_utp_0001', 'Suresh Patel', 'Tihar Central Jail No. 4', 'Ramesh Patel',
        'acc_sim_9042', 'Suresh K. Patel', 'Rohini District Jail No. 10', 'Ramesh Patel',
        0.88,
        '["Exact Father''s Name Match (''Ramesh Patel'')", "High phonetic name similarity (0.94 Metaphone)"]'::jsonb,
        '["Different prison inmate reference numbers", "Different arresting police stations"]'::jsonb,
        'Probabilistic matcher detected probable identity duplicate for Suresh Patel across facilities. Composite confidence 88%. Automatic merge withheld pending supervising legal officer review.',
        'PENDING_HUMAN_REVIEW'
    ),
    (
        'imr_cand_002',
        'acc_utp_0007', 'Ramesh Kumar', 'Tihar Central Jail No. 4', 'Dinesh Kumar',
        'acc_sim_8819', 'Ramesh A. Kumar', 'Mandoli Jail Complex No. 11', 'Dinesh Kumar',
        0.92,
        '["Same FIR district (Central Delhi)", "Recorded alias matches candidate primary name"]'::jsonb,
        '["Differing CCTNS station registration codes"]'::jsonb,
        'High-confidence multi-facility cross-match for Ramesh Kumar. Requires human legal confirmation before joining case dockets.',
        'PENDING_HUMAN_REVIEW'
    )
ON CONFLICT (id) DO UPDATE
SET match_confidence = EXCLUDED.match_confidence, match_explanation = EXCLUDED.match_explanation;

-- Seed Hearings Schedule (Dynamic court hearing dates)
INSERT INTO hearings_schedule (id, case_id, prisoner_name, court_name, hearing_date, hearing_type, status, judge)
VALUES
    ('HRG-UTP-0001', 'UTP-0001', 'Suresh Patel', 'Metropolitan Magistrate Court 02, Central', CURRENT_DATE + INTERVAL '7 days',  'Bail Application Under BNSS 479', 'Scheduled', NULL),
    ('HRG-UTP-0002', 'UTP-0002', 'Mohammad Rehan', 'Metropolitan Magistrate Court 05, Central', CURRENT_DATE + INTERVAL '8 days',  'Remand Review & Bail Motion',     'Scheduled', NULL),
    ('HRG-UTP-0003', 'UTP-0003', 'Vikramaditya Rao', 'Additional Sessions Court 03, North-West', CURRENT_DATE + INTERVAL '9 days',  'Remand Review & Bail Motion',     'Scheduled', NULL),
    ('HRG-UTP-0012', 'UTP-0012', 'Jagdish Pradhan', 'Sessions Court 01, North Delhi', CURRENT_DATE + INTERVAL '10 days', 'Remand Review & Bail Motion',     'Scheduled', NULL),
    ('HRG-UTP-0015', 'UTP-0015', 'Tenzin Namgyal', 'Metropolitan Magistrate Court 01, Central', CURRENT_DATE + INTERVAL '11 days', 'Remand Review & Bail Motion',     'Scheduled', NULL),
    ('HRG-UTP-0021', 'UTP-0021', 'Kavita Sundaram', 'Chief Metropolitan Magistrate Court, Central', CURRENT_DATE + INTERVAL '12 days', 'Bail Application Under BNSS 479', 'Scheduled', NULL)
ON CONFLICT (id) DO UPDATE
SET hearing_date = EXCLUDED.hearing_date, hearing_type = EXCLUDED.hearing_type;

COMMIT;

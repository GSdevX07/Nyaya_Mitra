-- Nyaya Mitra Supabase MISSING Tables Only
-- Run this in: https://supabase.com/dashboard/project/bqvgxarromdjjrzflrwy/sql/new

-- ── 1. Offenses Lookup ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS offenses (
    offense_code        VARCHAR(20) PRIMARY KEY,
    section             VARCHAR(50) NOT NULL,
    description         TEXT,
    max_sentence_days   INT NOT NULL
);

-- ── 2. Jails Lookup ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jails (
    jail_id         VARCHAR(20) PRIMARY KEY,
    jail_name       VARCHAR(255) NOT NULL,
    state           VARCHAR(100),
    occupancy_pct   INT
);

-- ── 3. Lawyers Lookup ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lawyers_lookup (
    lawyer_id       VARCHAR(20) PRIMARY KEY,
    lawyer_name     VARCHAR(255) NOT NULL,
    dlsa_district   VARCHAR(255)
);

-- ── 4. Bail Applications ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bail_applications (
    id                          VARCHAR(32) PRIMARY KEY,
    case_id                     VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    filed_date                  DATE,
    status                      VARCHAR(100) DEFAULT 'Filed - Awaiting Hearing',
    next_hearing_or_order_date  DATE,
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 5. Status Tracking ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS status_tracking (
    id              VARCHAR(32) PRIMARY KEY,
    application_id  VARCHAR(32) REFERENCES bail_applications(id) ON DELETE CASCADE,
    event           TEXT NOT NULL,
    event_date      DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── 6. Lawyers (active legal officers) ─────────────────────────────
CREATE TABLE IF NOT EXISTS lawyers (
    id                  VARCHAR(100) PRIMARY KEY,
    full_name           VARCHAR(255) NOT NULL,
    bar_association_id  VARCHAR(100) NOT NULL,
    email               VARCHAR(255) NOT NULL,
    phone               VARCHAR(50),
    specialization      VARCHAR(255) DEFAULT 'Criminal Defense & Statutory Bail',
    cases_taken         INT DEFAULT 0,
    status              VARCHAR(50) DEFAULT 'Active',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── 7. Case Lawyer Actions ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS case_lawyer_actions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    lawyer_id       VARCHAR(100) NOT NULL,
    action_type     VARCHAR(50) NOT NULL,
    acted_at        TIMESTAMPTZ DEFAULT NOW(),
    notes           TEXT
);

-- ── 8. Evidence Items ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evidence_items (
    id                  VARCHAR(32) PRIMARY KEY,
    case_id             VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    title               VARCHAR(255) NOT NULL,
    offense             TEXT NOT NULL,
    verification_status VARCHAR(50) DEFAULT 'Pending Verification',
    authenticity_score  FLOAT DEFAULT 74.0,
    chain_of_custody    TEXT,
    flagged             BOOLEAN DEFAULT FALSE,
    notes               TEXT,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── 9. Automated Actions ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS automated_actions (
    id           VARCHAR(64) PRIMARY KEY,
    case_id      VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    action_type  VARCHAR(100) NOT NULL,
    priority     VARCHAR(20) DEFAULT 'MEDIUM',
    status       VARCHAR(50) DEFAULT 'Ready for Approval',
    description  TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── 10. Hearings ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hearings (
    id             VARCHAR(32) PRIMARY KEY,
    case_id        VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    prisoner_name  VARCHAR(255) NOT NULL DEFAULT 'synthetic - not a real person',
    court_name     VARCHAR(255) NOT NULL,
    hearing_date   DATE NOT NULL,
    hearing_type   VARCHAR(100) NOT NULL,
    status         VARCHAR(50) DEFAULT 'Scheduled',
    judge          VARCHAR(255),
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ── 11. Case Approvals ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS case_approvals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    lawyer_id   VARCHAR(100) DEFAULT 'Legal Officer 104',
    approved_at TIMESTAMPTZ DEFAULT NOW(),
    status      VARCHAR(50) DEFAULT 'Approved by Human Lawyer',
    notes       TEXT
);

-- ── 12. Add missing columns to undertrial_cases ─────────────────────
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS offense_sections     TEXT[]       DEFAULT '{}';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS offense_code         VARCHAR(20);
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS jail_id              VARCHAR(20);
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS lawyer_id            VARCHAR(20);
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS arrest_date          DATE;
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS custody_days         INT          DEFAULT 0;
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS max_sentence_days_for_offense INT DEFAULT 0;
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS eligibility_threshold_days INT DEFAULT 0;
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS days_overdue         INT          DEFAULT 0;
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS eligibility_status   VARCHAR(50)  DEFAULT 'Not Yet Eligible';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS first_time_offender  BOOLEAN      DEFAULT TRUE;
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS age                  INT;
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS health_flag          BOOLEAN      DEFAULT FALSE;
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS preferred_language   VARCHAR(10)  DEFAULT 'en';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS present_docs         TEXT[]       DEFAULT '{}';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS records_complete     BOOLEAN      DEFAULT FALSE;
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS urgency_score        FLOAT        DEFAULT 0.0;
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS jail_location        VARCHAR(255) DEFAULT 'Synthetic Jail';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS status               VARCHAR(50)  DEFAULT 'DISCOVERED';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS relative_name        VARCHAR(255) DEFAULT 'Not Specified';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS relative_relation    VARCHAR(100) DEFAULT 'Parent/Relative';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS relative_phone       VARCHAR(50)  DEFAULT '+91 98765 00000';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS permanent_address    TEXT         DEFAULT 'Synthetic Address';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS assignment_status    VARCHAR(50)  DEFAULT 'AVAILABLE';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS assigned_lawyer_id   VARCHAR(100);
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS name                 VARCHAR(255) DEFAULT 'synthetic - not a real person';
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS created_at           TIMESTAMPTZ  DEFAULT NOW();
ALTER TABLE undertrial_cases ADD COLUMN IF NOT EXISTS updated_at           TIMESTAMPTZ  DEFAULT NOW();

-- ── 13. Indexes ─────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_cases_assignment ON undertrial_cases(assignment_status);
CREATE INDEX IF NOT EXISTS idx_cases_custody    ON undertrial_cases(custody_days);
CREATE INDEX IF NOT EXISTS idx_docs_case        ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_bail_case        ON bail_applications(case_id);
CREATE INDEX IF NOT EXISTS idx_tracking_app     ON status_tracking(application_id);

-- ── 14. Seed default lawyer ─────────────────────────────────────────
INSERT INTO lawyers (id, full_name, bar_association_id, email, phone, specialization, cases_taken)
VALUES (
    'Legal Officer 104', 'Adv. Rajesh Sharma', 'DL/2018/49281',
    'rajesh.sharma@nyayamitra.org', '+91 98112 34567',
    'Undertrial Defense & Section 479 BNSS', 3
) ON CONFLICT (id) DO NOTHING;

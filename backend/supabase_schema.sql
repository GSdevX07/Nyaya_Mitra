-- ═══════════════════════════════════════════════════════════════════
-- Nyaya Mitra Supabase Schema Migration
-- Run this FIRST in Supabase SQL Editor before seeding data
-- Project: bqvgxarromdjjrzflrwy
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. Offenses Lookup Table ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS offenses (
    offense_code        VARCHAR(20) PRIMARY KEY,
    section             VARCHAR(50) NOT NULL,
    description         TEXT,
    max_sentence_days   INT NOT NULL
);

-- ── 2. Jails Lookup Table ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jails (
    jail_id         VARCHAR(20) PRIMARY KEY,
    jail_name       VARCHAR(255) NOT NULL,
    state           VARCHAR(100),
    occupancy_pct   INT
);

-- ── 3. Lawyers Lookup Table ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lawyers_lookup (
    lawyer_id       VARCHAR(20) PRIMARY KEY,
    lawyer_name     VARCHAR(255) NOT NULL,
    dlsa_district   VARCHAR(255)
);

-- ── 4. Undertrial Cases Table (Enhanced) ─────────────────────────────
CREATE TABLE IF NOT EXISTS undertrial_cases (
    id                              VARCHAR(32) PRIMARY KEY,
    name                            VARCHAR(255) NOT NULL DEFAULT 'synthetic - not a real person',
    offense_code                    VARCHAR(20) REFERENCES offenses(offense_code),
    jail_id                         VARCHAR(20) REFERENCES jails(jail_id),
    lawyer_id                       VARCHAR(20) REFERENCES lawyers_lookup(lawyer_id),
    arrest_date                     DATE,
    custody_days                    INT NOT NULL DEFAULT 0,
    max_sentence_days_for_offense   INT NOT NULL DEFAULT 0,
    eligibility_threshold_days      INT DEFAULT 0,
    days_overdue                    INT DEFAULT 0,
    eligibility_status              VARCHAR(50) DEFAULT 'Not Yet Eligible',
    first_time_offender             BOOLEAN DEFAULT TRUE,
    age                             INT,
    health_flag                     BOOLEAN DEFAULT FALSE,
    preferred_language              VARCHAR(10) DEFAULT 'en',
    present_docs                    TEXT[] DEFAULT '{}',
    records_complete                BOOLEAN DEFAULT FALSE,
    urgency_score                   FLOAT DEFAULT 0.0,
    status                          VARCHAR(50) DEFAULT 'DISCOVERED',
    -- Lawyer assignment fields
    relative_name                   VARCHAR(255) DEFAULT 'Not Specified',
    relative_relation               VARCHAR(100) DEFAULT 'Parent/Relative',
    relative_phone                  VARCHAR(50)  DEFAULT '+91 98765 00000',
    permanent_address               TEXT         DEFAULT 'Synthetic Address',
    assignment_status               VARCHAR(50)  DEFAULT 'AVAILABLE',
    assigned_lawyer_id              VARCHAR(100),
    created_at                      TIMESTAMPTZ DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ DEFAULT NOW()
);

-- ── 5. Documents Table ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              VARCHAR(64) PRIMARY KEY,
    case_id         VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    document_type   VARCHAR(100) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'missing',
    is_present      BOOLEAN DEFAULT FALSE,
    file_url        TEXT,
    uploaded_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── 6. Bail Applications Table ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS bail_applications (
    id                          VARCHAR(32) PRIMARY KEY,
    case_id                     VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    filed_date                  DATE,
    status                      VARCHAR(100) DEFAULT 'Filed - Awaiting Hearing',
    next_hearing_or_order_date  DATE,
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 7. Status Tracking Table ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS status_tracking (
    id              VARCHAR(32) PRIMARY KEY,
    application_id  VARCHAR(32) REFERENCES bail_applications(id) ON DELETE CASCADE,
    event           TEXT NOT NULL,
    event_date      DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── 8. Lawyers (active legal officers) Table ─────────────────────────
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

-- ── 9. Case Lawyer Actions (Approvals/Declines) ───────────────────────
CREATE TABLE IF NOT EXISTS case_lawyer_actions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    lawyer_id       VARCHAR(100) NOT NULL,
    action_type     VARCHAR(50) NOT NULL, -- 'APPROVED' | 'DECLINED'
    acted_at        TIMESTAMPTZ DEFAULT NOW(),
    notes           TEXT
);

-- ── 10. Notifications Table ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id          VARCHAR(32) PRIMARY KEY,
    case_id     VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE SET NULL,
    title       VARCHAR(255) NOT NULL,
    message     TEXT NOT NULL,
    type        VARCHAR(20) DEFAULT 'info',
    read        BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 11. Evidence Items Table ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evidence_items (
    id                      VARCHAR(32) PRIMARY KEY,
    case_id                 VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    title                   VARCHAR(255) NOT NULL,
    offense                 TEXT NOT NULL,
    verification_status     VARCHAR(50) DEFAULT 'Pending Verification',
    authenticity_score      FLOAT DEFAULT 74.0,
    chain_of_custody        TEXT,
    flagged                 BOOLEAN DEFAULT FALSE,
    notes                   TEXT,
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── 12. Automated Actions Table ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS automated_actions (
    id              VARCHAR(64) PRIMARY KEY,
    case_id         VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    action_type     VARCHAR(100) NOT NULL,
    priority        VARCHAR(20) DEFAULT 'MEDIUM',
    status          VARCHAR(50) DEFAULT 'Ready for Approval',
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── 13. Hearings Table ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hearings (
    id              VARCHAR(32) PRIMARY KEY,
    case_id         VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    prisoner_name   VARCHAR(255) NOT NULL DEFAULT 'synthetic - not a real person',
    court_name      VARCHAR(255) NOT NULL,
    hearing_date    DATE NOT NULL,
    hearing_type    VARCHAR(100) NOT NULL,
    status          VARCHAR(50) DEFAULT 'Scheduled',
    judge           VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── 14. Case Approvals Table ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS case_approvals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    lawyer_id   VARCHAR(100) DEFAULT 'Legal Officer 104',
    approved_at TIMESTAMPTZ DEFAULT NOW(),
    status      VARCHAR(50) DEFAULT 'Approved by Human Lawyer',
    notes       TEXT
);

-- ── Indexes ──────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_cases_offense       ON undertrial_cases(offense_code);
CREATE INDEX IF NOT EXISTS idx_cases_jail          ON undertrial_cases(jail_id);
CREATE INDEX IF NOT EXISTS idx_cases_assignment    ON undertrial_cases(assignment_status);
CREATE INDEX IF NOT EXISTS idx_cases_custody       ON undertrial_cases(custody_days);
CREATE INDEX IF NOT EXISTS idx_docs_case           ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_bail_case           ON bail_applications(case_id);
CREATE INDEX IF NOT EXISTS idx_tracking_app        ON status_tracking(application_id);
CREATE INDEX IF NOT EXISTS idx_hearings_date       ON hearings(hearing_date);

-- ── Seed default active lawyer ───────────────────────────────────────
INSERT INTO lawyers (id, full_name, bar_association_id, email, phone, specialization, cases_taken)
VALUES (
    'Legal Officer 104',
    'Adv. Rajesh Sharma',
    'DL/2018/49281',
    'rajesh.sharma@nyayamitra.org',
    '+91 98112 34567',
    'Undertrial Defense & Section 479 BNSS',
    3
) ON CONFLICT (id) DO NOTHING;

-- ── Enable Row Level Security (optional, service key bypasses) ────────
ALTER TABLE undertrial_cases      ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents             ENABLE ROW LEVEL SECURITY;
ALTER TABLE bail_applications     ENABLE ROW LEVEL SECURITY;
ALTER TABLE status_tracking       ENABLE ROW LEVEL SECURITY;
ALTER TABLE lawyers               ENABLE ROW LEVEL SECURITY;
ALTER TABLE offenses              ENABLE ROW LEVEL SECURITY;
ALTER TABLE jails                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE lawyers_lookup        ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications         ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_lawyer_actions   ENABLE ROW LEVEL SECURITY;

-- Allow full access for service_role
CREATE POLICY "Service role full access on undertrial_cases"   ON undertrial_cases     FOR ALL USING (true);
CREATE POLICY "Service role full access on documents"          ON documents            FOR ALL USING (true);
CREATE POLICY "Service role full access on bail_applications"  ON bail_applications    FOR ALL USING (true);
CREATE POLICY "Service role full access on status_tracking"    ON status_tracking      FOR ALL USING (true);
CREATE POLICY "Service role full access on lawyers"            ON lawyers              FOR ALL USING (true);
CREATE POLICY "Service role full access on offenses"           ON offenses             FOR ALL USING (true);
CREATE POLICY "Service role full access on jails"              ON jails                FOR ALL USING (true);
CREATE POLICY "Service role full access on lawyers_lookup"     ON lawyers_lookup       FOR ALL USING (true);
CREATE POLICY "Service role full access on notifications"      ON notifications        FOR ALL USING (true);
CREATE POLICY "Service role full access on case_lawyer_actions" ON case_lawyer_actions FOR ALL USING (true);

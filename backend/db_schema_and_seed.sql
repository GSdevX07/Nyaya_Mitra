-- ─────────────────────────────────────────────────────────────────────────────
-- Nyaya Mitra Database Schema Enhancement & Seed Script
-- Supports: Available Cases Pool, Lawyer Assignments, Family Contact Details & Address
-- ─────────────────────────────────────────────────────────────────────────────

-- ── 1. Undertrial Cases Table (Original + Enhancements) ───────────────────────
CREATE TABLE IF NOT EXISTS undertrial_cases (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL DEFAULT 'synthetic - not a real person',
    offense_sections TEXT[] NOT NULL,
    arrest_date DATE NOT NULL,
    custody_days INT NOT NULL DEFAULT 0,
    max_sentence_days_for_offense INT NOT NULL,
    prior_bail_orders TEXT[] DEFAULT '{}',
    jail_location VARCHAR(255) NOT NULL,
    preferred_language VARCHAR(10) DEFAULT 'en',
    status VARCHAR(50) DEFAULT 'DISCOVERED',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add Contact & Lawyer Assignment Columns
ALTER TABLE undertrial_cases 
ADD COLUMN IF NOT EXISTS relative_name VARCHAR(255) DEFAULT 'Not Specified',
ADD COLUMN IF NOT EXISTS relative_relation VARCHAR(100) DEFAULT 'Parent/Relative',
ADD COLUMN IF NOT EXISTS relative_phone VARCHAR(50) DEFAULT '+91 98765 43210',
ADD COLUMN IF NOT EXISTS permanent_address TEXT DEFAULT 'Synthetic Address, District Detention Zone',
ADD COLUMN IF NOT EXISTS assignment_status VARCHAR(50) DEFAULT 'AVAILABLE', -- 'AVAILABLE', 'ASSIGNED', 'DECLINED'
ADD COLUMN IF NOT EXISTS assigned_lawyer_id VARCHAR(100) DEFAULT NULL;

-- ── 2. Urgency Flags Table ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS urgency_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    age INT NOT NULL,
    health_flag BOOLEAN DEFAULT FALSE,
    repeat_offender BOOLEAN DEFAULT FALSE,
    computed_urgency_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 3. Documents Table ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    document_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'missing',
    is_present BOOLEAN DEFAULT FALSE,
    file_url TEXT,
    uploaded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 4. Evidence Items Table ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evidence_items (
    id VARCHAR(32) PRIMARY KEY,
    case_id VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    offense TEXT NOT NULL,
    verification_status VARCHAR(50) DEFAULT 'Pending Verification',
    authenticity_score FLOAT DEFAULT 74.0,
    chain_of_custody TEXT,
    flagged BOOLEAN DEFAULT FALSE,
    notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 5. Automated Actions Table ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS automated_actions (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    status VARCHAR(50) DEFAULT 'Ready for Approval',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 6. Hearings Table ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hearings (
    id VARCHAR(32) PRIMARY KEY,
    case_id VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    prisoner_name VARCHAR(255) NOT NULL,
    court_name VARCHAR(255) NOT NULL,
    hearing_date DATE NOT NULL,
    hearing_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'Scheduled',
    judge VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 7. Notifications Table ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(32) PRIMARY KEY,
    case_id VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(20) DEFAULT 'info',
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 8. Case Approvals Table ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS case_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    lawyer_id VARCHAR(100) DEFAULT 'Legal Officer 104',
    approved_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'Approved by Human Lawyer',
    notes TEXT
);

-- ── 9. Lawyers Table (NEW) ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lawyers (
    id VARCHAR(100) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    bar_association_id VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    specialization VARCHAR(100) DEFAULT 'Criminal Defense & Statutory Bail',
    cases_taken INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'Active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 10. Case Lawyer Actions Table (NEW - Tracking Approvals & Declines) ──────
CREATE TABLE IF NOT EXISTS case_lawyer_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(32) REFERENCES undertrial_cases(id) ON DELETE CASCADE,
    lawyer_id VARCHAR(100) NOT NULL,
    action_type VARCHAR(50) NOT NULL, -- 'APPROVED', 'DECLINED'
    acted_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);

-- ── Indexes for Fast Querying ───────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_undertrial_custody ON undertrial_cases(custody_days);
CREATE INDEX IF NOT EXISTS idx_documents_case ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence_items(case_id);
CREATE INDEX IF NOT EXISTS idx_actions_case ON automated_actions(case_id);
CREATE INDEX IF NOT EXISTS idx_hearings_date ON hearings(hearing_date);
CREATE INDEX IF NOT EXISTS idx_undertrial_assignment ON undertrial_cases(assignment_status);

-- ── Seed Data for Lawyers & Family Contacts ──────────────────────────────────
INSERT INTO lawyers (id, full_name, bar_association_id, email, phone, specialization, cases_taken)
VALUES ('Legal Officer 104', 'Adv. Rajesh Sharma', 'DL/2018/49281', 'rajesh.sharma@nyayamitra.org', '+91 98112 34567', 'Undertrial Defense & Section 479 BNSS', 3)
ON CONFLICT (id) DO NOTHING;

-- Populate synthetic relative names, relations, phone numbers, and addresses
UPDATE undertrial_cases SET 
    relative_name = 'Ramesh Kumar (Father)',
    relative_relation = 'Father',
    relative_phone = '+91 98765 11001',
    permanent_address = 'Plot 42, Gandhi Nagar, Sector 4, Chennai, TN - 600001',
    assignment_status = 'AVAILABLE'
WHERE id = 'UTP-0001';

UPDATE undertrial_cases SET 
    relative_name = 'Sunita Devi (Wife)',
    relative_relation = 'Spouse',
    relative_phone = '+91 98765 77007',
    permanent_address = 'Flat 12B, Old City Suburb, Jaipur, RJ - 302001',
    assignment_status = 'AVAILABLE'
WHERE id = 'UTP-0007';

UPDATE undertrial_cases SET 
    relative_name = 'Mohd. Ahmed (Brother)',
    relative_relation = 'Brother',
    relative_phone = '+91 98765 12012',
    permanent_address = 'House 88, Shivaji Road, Bengaluru, KA - 560002',
    assignment_status = 'AVAILABLE'
WHERE id = 'UTP-0012';

UPDATE undertrial_cases SET 
    relative_name = 'Anand Singh (Father)',
    relative_relation = 'Father',
    relative_phone = '+91 98765 15015',
    permanent_address = 'Village Rampur, Post Office Sub-Jail Zone, Lucknow, UP - 226001',
    assignment_status = 'AVAILABLE'
WHERE id = 'UTP-0015';

UPDATE undertrial_cases SET 
    relative_name = 'Kamla Prasad (Son)',
    relative_relation = 'Son',
    relative_phone = '+91 98765 21021',
    permanent_address = 'H.No 304, Green Avenue, Hyderabad, TS - 500001',
    assignment_status = 'AVAILABLE'
WHERE id = 'UTP-0021';

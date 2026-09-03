-- ============================================================================
-- Nyaya Mitra: Supabase Stage 03 Full Parity Migration
-- Run this script in the Supabase SQL Editor to bring Supabase PostgreSQL
-- into 100% full schema parity with the Nyaya Mitra backend and SQLite database.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. EXTENSIONS & PREREQUISITES
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ----------------------------------------------------------------------------
-- 2. ENHANCE EXISTING TABLES WITH ALL MISSING COLUMNS
-- ----------------------------------------------------------------------------

-- Organization Users (Advocate credentials & supervision)
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS bar_registration_no VARCHAR(100);
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS years_of_experience INTEGER;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS specialization VARCHAR(255);
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS empanelment_category VARCHAR(100);
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS supervision_required BOOLEAN DEFAULT false;

-- Accused Persons (Full CCTNS, demographic, and identity resolution fields)
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS date_of_birth VARCHAR(50);
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS prison_inmate_no VARCHAR(100);
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS cctns_person_id VARCHAR(100);
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS alias_names JSONB DEFAULT '[]'::jsonb;
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS aadhaar_hash VARCHAR(128);
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS voter_id_masked VARCHAR(50);
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS source_system VARCHAR(100) DEFAULT 'DEMO_SYNTHETIC';
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS source_record_id VARCHAR(100);
ALTER TABLE accused_persons ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMPTZ DEFAULT NOW();

-- FIRs (Police station scoping)
ALTER TABLE firs ADD COLUMN IF NOT EXISTS police_station_id VARCHAR(64);

-- Court Cases (Police station scoping)
ALTER TABLE court_cases ADD COLUMN IF NOT EXISTS police_station_id VARCHAR(64);

-- Uploaded Documents (Monotonic versioning, security scan, and audience visibility)
ALTER TABLE uploaded_documents ADD COLUMN IF NOT EXISTS authoritative_source BOOLEAN DEFAULT false;
ALTER TABLE uploaded_documents ADD COLUMN IF NOT EXISTS current_version INTEGER DEFAULT 1;
ALTER TABLE uploaded_documents ADD COLUMN IF NOT EXISTS document_status VARCHAR(50) DEFAULT 'PENDING_VERIFICATION';
ALTER TABLE uploaded_documents ADD COLUMN IF NOT EXISTS security_scan_status VARCHAR(50) DEFAULT 'CLEAN';
ALTER TABLE uploaded_documents ADD COLUMN IF NOT EXISTS security_scan_details TEXT;
ALTER TABLE uploaded_documents ADD COLUMN IF NOT EXISTS source_authority VARCHAR(100) DEFAULT 'INSTITUTIONAL';
ALTER TABLE uploaded_documents ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE uploaded_documents ADD COLUMN IF NOT EXISTS uploaded_by VARCHAR(64);
ALTER TABLE uploaded_documents ADD COLUMN IF NOT EXISTS citizen_visible BOOLEAN DEFAULT true;
ALTER TABLE uploaded_documents ADD COLUMN IF NOT EXISTS family_visible BOOLEAN DEFAULT true;

-- Notifications (Role and user targeted dispatch)
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS target_role VARCHAR(64);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS user_id VARCHAR(64);

-- Audit Events (Cryptographic hash-chaining and immutability triggers)
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS event_hash VARCHAR(128);
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS previous_event_hash VARCHAR(128);
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS hash_algorithm VARCHAR(32) DEFAULT 'SHA-256';
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS sequence_number BIGINT;
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS severity VARCHAR(32) DEFAULT 'INFO';
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS data_status VARCHAR(32) DEFAULT 'COMMITTED';

-- ----------------------------------------------------------------------------
-- 3. CREATE 12 MISSING INSTITUTIONAL TABLES
-- ----------------------------------------------------------------------------

-- Table 1: Family Contacts (Normalized next-of-kin emergency and assistance registry)
CREATE TABLE IF NOT EXISTS family_contacts (
    id VARCHAR(64) PRIMARY KEY,
    accused_id VARCHAR(64) NOT NULL REFERENCES accused_persons(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    relation VARCHAR(100),
    phone VARCHAR(50),
    alt_phone VARCHAR(50),
    address TEXT,
    preferred_language VARCHAR(20) DEFAULT 'hi',
    preferred_channel VARCHAR(20) DEFAULT 'SMS',
    is_primary_contact BOOLEAN DEFAULT false,
    verified_by_dlsa BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 2: Identity Merge Candidates (Probabilistic de-duplication review queue)
CREATE TABLE IF NOT EXISTS identity_merge_candidates (
    id VARCHAR(64) PRIMARY KEY,
    source_accused_id VARCHAR(64) NOT NULL REFERENCES accused_persons(id) ON DELETE CASCADE,
    source_name VARCHAR(255),
    source_facility VARCHAR(255),
    source_father_name VARCHAR(255),
    source_dob VARCHAR(50),
    candidate_accused_id VARCHAR(64) NOT NULL REFERENCES accused_persons(id) ON DELETE CASCADE,
    candidate_name VARCHAR(255),
    candidate_facility VARCHAR(255),
    candidate_father_name VARCHAR(255),
    candidate_dob VARCHAR(50),
    match_confidence DOUBLE PRECISION DEFAULT 0.0,
    shared_traits JSONB DEFAULT '[]'::jsonb,
    conflicting_traits JSONB DEFAULT '[]'::jsonb,
    match_explanation TEXT,
    review_status VARCHAR(64) DEFAULT 'PENDING_HUMAN_REVIEW',
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 3: Hearings Schedule (Court calendar, judge, and hearing tracking)
CREATE TABLE IF NOT EXISTS hearings_schedule (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    prisoner_name VARCHAR(255),
    court_name VARCHAR(255) NOT NULL,
    hearing_date VARCHAR(50) NOT NULL,
    hearing_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'Scheduled',
    judge VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 4: Police Actions (ICJS procedural requests, remand extension, chargesheet dispatch)
CREATE TABLE IF NOT EXISTS police_actions (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    police_station_id VARCHAR(64) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    requested_by VARCHAR(64) DEFAULT 'DLSA_OFFICER',
    status VARCHAR(50) DEFAULT 'PENDING',
    document_id VARCHAR(64),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Table 5: Document Processing Versions (Immutable OCR snapshots & version history)
CREATE TABLE IF NOT EXISTS document_processing_versions (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES uploaded_documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    parent_version_id VARCHAR(64),
    processing_status VARCHAR(50) DEFAULT 'SUCCESS',
    ocr_engine VARCHAR(100),
    ocr_confidence DOUBLE PRECISION DEFAULT 1.0,
    is_handwritten BOOLEAN DEFAULT false,
    manual_verification_required BOOLEAN DEFAULT false,
    needs_human_verification_reason TEXT,
    raw_text TEXT,
    normalized_text TEXT,
    classification VARCHAR(100),
    extracted_facts_json JSONB DEFAULT '[]'::jsonb,
    rag_citations_json JSONB DEFAULT '[]'::jsonb,
    assessment_summary_json JSONB DEFAULT '{}'::jsonb,
    processed_by VARCHAR(64),
    processing_time_ms DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 6: Document Field Corrections (Human-in-the-loop verified audit trail)
CREATE TABLE IF NOT EXISTS document_field_corrections (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES uploaded_documents(id) ON DELETE CASCADE,
    version_id VARCHAR(64),
    field_name VARCHAR(100) NOT NULL,
    original_machine_value TEXT,
    corrected_value TEXT NOT NULL,
    source_span TEXT,
    correction_reason TEXT NOT NULL,
    corrected_by VARCHAR(64) NOT NULL,
    corrected_by_role VARCHAR(64) NOT NULL,
    corrected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 7: Document Access Logs (Chain of custody access & download logging)
CREATE TABLE IF NOT EXISTS document_access_logs (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL,
    case_id VARCHAR(64) NOT NULL,
    action VARCHAR(50) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    user_role VARCHAR(64) NOT NULL,
    ip_address VARCHAR(45),
    details_json JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Table 8: Legal Sources (Governed statutory knowledge registry - BNSS, BNS, CrPC, IPC)
CREATE TABLE IF NOT EXISTS legal_sources (
    id VARCHAR(64) PRIMARY KEY,
    title TEXT NOT NULL,
    short_name VARCHAR(100),
    issuing_authority VARCHAR(255) NOT NULL,
    effective_date VARCHAR(50) NOT NULL,
    publication_date VARCHAR(50),
    jurisdiction VARCHAR(100) NOT NULL,
    source_url TEXT,
    document_hash VARCHAR(128) NOT NULL,
    version VARCHAR(20) DEFAULT '1.0',
    language VARCHAR(20) DEFAULT 'en',
    legal_domain VARCHAR(100) NOT NULL,
    lifecycle_status VARCHAR(50) DEFAULT 'discovered',
    superseded_by_id VARCHAR(64) REFERENCES legal_sources(id),
    raw_content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_by VARCHAR(64),
    approved_by VARCHAR(64),
    audit_notes TEXT
);

-- Table 9: Legal Chunks (Chunk-level statutory embeddings and citations)
CREATE TABLE IF NOT EXISTS legal_chunks (
    id VARCHAR(64) PRIMARY KEY,
    source_id VARCHAR(64) NOT NULL REFERENCES legal_sources(id) ON DELETE CASCADE,
    document_title VARCHAR(255) NOT NULL,
    section_number VARCHAR(100),
    section_title TEXT,
    original_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    start_char INTEGER DEFAULT 0,
    end_char INTEGER DEFAULT 0,
    citation_key VARCHAR(100),
    legal_domain VARCHAR(100),
    jurisdiction VARCHAR(100),
    metadata_json JSONB DEFAULT '{}'::jsonb
);

-- Table 10: Legal Evaluation Benchmarks (Grounding quality benchmarks)
CREATE TABLE IF NOT EXISTS legal_evaluation_benchmarks (
    id VARCHAR(64) PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_category VARCHAR(100) NOT NULL,
    expected_source_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_citation_keys_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_statute VARCHAR(100),
    difficulty VARCHAR(50) DEFAULT 'STANDARD',
    last_recall_score DOUBLE PRECISION DEFAULT 0.0,
    last_evaluated_at TIMESTAMPTZ
);

-- Table 11: Legal Retrieval Logs (Statutory RAG provenance & citations telemetry)
CREATE TABLE IF NOT EXISTS legal_retrieval_logs (
    id VARCHAR(64) PRIMARY KEY,
    query_id VARCHAR(64),
    actor_id VARCHAR(64),
    actor_role VARCHAR(64),
    organization_id VARCHAR(64),
    query_text TEXT NOT NULL,
    source_ids_json JSONB DEFAULT '[]'::jsonb,
    source_versions_json JSONB DEFAULT '[]'::jsonb,
    matched_citation_keys_json JSONB DEFAULT '[]'::jsonb,
    relevance_scores_json JSONB DEFAULT '[]'::jsonb,
    selected_passages_json JSONB DEFAULT '[]'::jsonb,
    used_superseded BOOLEAN DEFAULT false,
    grounding_score DOUBLE PRECISION DEFAULT 0.0,
    routed_to_human_review BOOLEAN DEFAULT false,
    status VARCHAR(50) DEFAULT 'SUCCESS',
    queried_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 12: Legal Human Review Tasks (Hallucination prevention & supervisory escalations)
CREATE TABLE IF NOT EXISTS legal_human_review_tasks (
    id VARCHAR(64) PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    actor_id VARCHAR(64) NOT NULL,
    actor_role VARCHAR(64) NOT NULL,
    case_id VARCHAR(64),
    statement_hash VARCHAR(128) NOT NULL,
    draft_statement TEXT NOT NULL,
    unsupported_citations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    retrieved_context_json JSONB DEFAULT '[]'::jsonb,
    grounding_score DOUBLE PRECISION NOT NULL,
    escalation_reason TEXT NOT NULL,
    assigned_role VARCHAR(64) DEFAULT 'SUPERVISING_LEGAL_OFFICER',
    assigned_user_id VARCHAR(64),
    review_status VARCHAR(50) DEFAULT 'PENDING_REVIEW',
    resolution_notes TEXT,
    resolved_by VARCHAR(64),
    resolved_at TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- 4. PERFORMANCE & SCOPING INDEXES
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_family_contacts_accused ON family_contacts(accused_id);
CREATE INDEX IF NOT EXISTS idx_merge_candidates_status ON identity_merge_candidates(review_status);
CREATE INDEX IF NOT EXISTS idx_hearings_case_id ON hearings_schedule(case_id);
CREATE INDEX IF NOT EXISTS idx_hearings_date ON hearings_schedule(hearing_date);
CREATE INDEX IF NOT EXISTS idx_police_actions_station ON police_actions(police_station_id, status);
CREATE INDEX IF NOT EXISTS idx_doc_versions_doc_id ON document_processing_versions(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_corrections_doc_id ON document_field_corrections(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_access_logs_doc ON document_access_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_source ON legal_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_citation ON legal_chunks(citation_key);
CREATE INDEX IF NOT EXISTS idx_retrieval_logs_query ON legal_retrieval_logs(query_id);
CREATE INDEX IF NOT EXISTS idx_human_review_status ON legal_human_review_tasks(review_status);

-- ----------------------------------------------------------------------------
-- 5. IMMUTABILITY TRIGGER FOR AUDIT_EVENTS
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_audit_events_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit ledger events are cryptographically immutable. UPDATE or DELETE operations are strictly prohibited by law.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_audit_events_update ON audit_events;
CREATE TRIGGER trg_prevent_audit_events_update
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION prevent_audit_events_modification();

-- ----------------------------------------------------------------------------
-- 6. ROW LEVEL SECURITY (RLS) POLICIES
-- ----------------------------------------------------------------------------
ALTER TABLE family_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_merge_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE hearings_schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE police_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_processing_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_field_corrections ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE legal_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE legal_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE legal_evaluation_benchmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE legal_retrieval_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE legal_human_review_tasks ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS for backend operations
CREATE POLICY service_role_all_family_contacts ON family_contacts FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_merge_candidates ON identity_merge_candidates FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_hearings ON hearings_schedule FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_police_actions ON police_actions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_doc_versions ON document_processing_versions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_doc_corrections ON document_field_corrections FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_doc_access_logs ON document_access_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_legal_sources ON legal_sources FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_legal_chunks ON legal_chunks FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_legal_benchmarks ON legal_evaluation_benchmarks FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_retrieval_logs ON legal_retrieval_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_human_review_tasks ON legal_human_review_tasks FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ==============================================================================
-- Nyaya Mitra - Complete Supabase PostgreSQL Schema & Missing Tables Migration
-- Run this script in the Supabase SQL Editor (Dashboard -> SQL Editor -> New Query)
-- It is completely IDEMPOTENT: safe to run multiple times without data loss.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. CREATE MISSING TABLES
-- ------------------------------------------------------------------------------

-- 1.1 Document Access Logs (Audit trail for document downloads, views, and inspections)
CREATE TABLE IF NOT EXISTS public.document_access_logs (
    id TEXT PRIMARY KEY,
    document_id TEXT,
    case_id TEXT,
    action TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_role TEXT NOT NULL,
    ip_address TEXT DEFAULT '127.0.0.1',
    details_json JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_doc_access_logs_doc_id ON public.document_access_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_access_logs_case_id ON public.document_access_logs(case_id);
CREATE INDEX IF NOT EXISTS idx_doc_access_logs_user_id ON public.document_access_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_doc_access_logs_action ON public.document_access_logs(action);
CREATE INDEX IF NOT EXISTS idx_doc_access_logs_timestamp ON public.document_access_logs(timestamp DESC);

-- 1.2 Document Field Corrections (Human-in-the-loop review adjustments)
CREATE TABLE IF NOT EXISTS public.document_field_corrections (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    version_id TEXT,
    field_name TEXT NOT NULL,
    original_machine_value TEXT,
    corrected_value TEXT NOT NULL,
    source_span TEXT,
    correction_reason TEXT NOT NULL,
    corrected_by TEXT NOT NULL,
    corrected_by_role TEXT NOT NULL,
    corrected_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_doc_field_corrections_doc_id ON public.document_field_corrections(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_field_corrections_field ON public.document_field_corrections(field_name);
CREATE INDEX IF NOT EXISTS idx_doc_field_corrections_at ON public.document_field_corrections(corrected_at DESC);

-- 1.3 Document Processing Versions (Immutable N+1 versioning for OCR & text extraction)
CREATE TABLE IF NOT EXISTS public.document_processing_versions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    parent_version_id TEXT,
    processing_status TEXT NOT NULL DEFAULT 'SUCCESS',
    ocr_engine TEXT,
    ocr_confidence NUMERIC(5,4),
    is_handwritten BOOLEAN DEFAULT false,
    manual_verification_required BOOLEAN DEFAULT false,
    needs_human_verification_reason TEXT,
    raw_text TEXT,
    normalized_text TEXT,
    classification TEXT,
    extracted_facts_json JSONB DEFAULT '{}'::jsonb,
    rag_citations_json JSONB DEFAULT '[]'::jsonb,
    assessment_summary_json JSONB DEFAULT '{}'::jsonb,
    processed_by TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_doc_versions_doc_id ON public.document_processing_versions(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_versions_number ON public.document_processing_versions(document_id, version_number);
CREATE INDEX IF NOT EXISTS idx_doc_versions_created ON public.document_processing_versions(created_at DESC);

-- 1.4 Police Actions (Operational desk tasks, document requests & verifications)
CREATE TABLE IF NOT EXISTS public.police_actions (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    police_station_id TEXT,
    action_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    requested_by TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    document_id TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_police_actions_case_id ON public.police_actions(case_id);
CREATE INDEX IF NOT EXISTS idx_police_actions_station_id ON public.police_actions(police_station_id);
CREATE INDEX IF NOT EXISTS idx_police_actions_status ON public.police_actions(status);
CREATE INDEX IF NOT EXISTS idx_police_actions_created ON public.police_actions(created_at DESC);

-- 1.5 Revoked Tokens (JWT blacklist for logout and token invalidation)
CREATE TABLE IF NOT EXISTS public.revoked_tokens (
    jti TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_revoked_tokens_user_id ON public.revoked_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires_at ON public.revoked_tokens(expires_at);


-- ------------------------------------------------------------------------------
-- 2. ALTER EXISTING TABLES TO ADD MISSING COLUMNS
-- ------------------------------------------------------------------------------

-- 2.1 audit_events: Add cryptographic sequence, event hash, severity, and status
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS event_hash TEXT;
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS previous_event_hash TEXT;
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS hash_algorithm TEXT DEFAULT 'SHA-256';
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS sequence_number BIGINT;
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS severity TEXT DEFAULT 'INFO';
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS data_status TEXT DEFAULT 'REAL';

CREATE INDEX IF NOT EXISTS idx_audit_events_event_hash ON public.audit_events(event_hash);
CREATE INDEX IF NOT EXISTS idx_audit_events_seq ON public.audit_events(sequence_number);
CREATE INDEX IF NOT EXISTS idx_audit_events_severity ON public.audit_events(severity);

-- 2.2 uploaded_documents: Add Stage 7 security scanning, lifecycle & audience controls
ALTER TABLE public.uploaded_documents ADD COLUMN IF NOT EXISTS source_authority TEXT DEFAULT 'INSTITUTIONAL';
ALTER TABLE public.uploaded_documents ADD COLUMN IF NOT EXISTS uploaded_by TEXT;
ALTER TABLE public.uploaded_documents ADD COLUMN IF NOT EXISTS document_status TEXT DEFAULT 'PENDING_VERIFICATION';
ALTER TABLE public.uploaded_documents ADD COLUMN IF NOT EXISTS authoritative_source BOOLEAN DEFAULT false;
ALTER TABLE public.uploaded_documents ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE public.uploaded_documents ADD COLUMN IF NOT EXISTS security_scan_status TEXT DEFAULT 'PASSED';
ALTER TABLE public.uploaded_documents ADD COLUMN IF NOT EXISTS security_scan_details JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.uploaded_documents ADD COLUMN IF NOT EXISTS current_version INTEGER DEFAULT 1;
ALTER TABLE public.uploaded_documents ADD COLUMN IF NOT EXISTS citizen_visible BOOLEAN DEFAULT true;
ALTER TABLE public.uploaded_documents ADD COLUMN IF NOT EXISTS family_visible BOOLEAN DEFAULT true;

CREATE INDEX IF NOT EXISTS idx_uploaded_documents_status ON public.uploaded_documents(document_status);
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_authority ON public.uploaded_documents(source_authority);

-- 2.3 court_cases: Add police station linking
ALTER TABLE public.court_cases ADD COLUMN IF NOT EXISTS police_station_id TEXT;
CREATE INDEX IF NOT EXISTS idx_court_cases_station_id ON public.court_cases(police_station_id);

-- 2.4 firs: Add police station linking
ALTER TABLE public.firs ADD COLUMN IF NOT EXISTS police_station_id TEXT;
CREATE INDEX IF NOT EXISTS idx_firs_station_id ON public.firs(police_station_id);

-- 2.5 organization_users: Add updated_at timestamp
ALTER TABLE public.organization_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());

-- 2.6 bail_applications: Verify sign-off and filing columns
ALTER TABLE public.bail_applications ADD COLUMN IF NOT EXISTS advocate_signed_off BOOLEAN DEFAULT false;
ALTER TABLE public.bail_applications ADD COLUMN IF NOT EXISTS signed_off_by_user_id TEXT;
ALTER TABLE public.bail_applications ADD COLUMN IF NOT EXISTS signed_off_at TIMESTAMPTZ;
ALTER TABLE public.bail_applications ADD COLUMN IF NOT EXISTS court_filing_reference TEXT;
ALTER TABLE public.bail_applications ADD COLUMN IF NOT EXISTS is_filed BOOLEAN DEFAULT false;
ALTER TABLE public.bail_applications ADD COLUMN IF NOT EXISTS filing_date TIMESTAMPTZ;


-- ------------------------------------------------------------------------------
-- 3. ROW LEVEL SECURITY (RLS) POLICIES
-- ------------------------------------------------------------------------------

-- Enable RLS on newly created tables
ALTER TABLE public.document_access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_field_corrections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_processing_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.police_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.revoked_tokens ENABLE ROW LEVEL SECURITY;

-- Create permissive service_role / authenticated backend access policies
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'document_access_logs' AND policyname = 'Allow access to document_access_logs'
    ) THEN
        CREATE POLICY "Allow access to document_access_logs" ON public.document_access_logs FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'document_field_corrections' AND policyname = 'Allow access to document_field_corrections'
    ) THEN
        CREATE POLICY "Allow access to document_field_corrections" ON public.document_field_corrections FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'document_processing_versions' AND policyname = 'Allow access to document_processing_versions'
    ) THEN
        CREATE POLICY "Allow access to document_processing_versions" ON public.document_processing_versions FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'police_actions' AND policyname = 'Allow access to police_actions'
    ) THEN
        CREATE POLICY "Allow access to police_actions" ON public.police_actions FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'revoked_tokens' AND policyname = 'Allow access to revoked_tokens'
    ) THEN
        CREATE POLICY "Allow access to revoked_tokens" ON public.revoked_tokens FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;


-- ------------------------------------------------------------------------------
-- 4. REFRESH POSTGREST SCHEMA CACHE
-- ------------------------------------------------------------------------------
-- This notifies PostgREST to immediately reload its table and column schema cache
NOTIFY pgrst, 'reload schema';

-- Verification confirmation query
SELECT 
    'Schema Migration Successfully Completed!' AS status,
    timezone('utc'::text, now()) AS completed_at;

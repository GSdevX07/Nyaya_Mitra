-- ==============================================================================
-- NYAYA MITRA: MASTER SUPABASE POSTGRESQL SYNC MIGRATION
-- Run this in the Supabase SQL Editor (Dashboard -> SQL Editor -> New Query)
-- Can be run ALL AT ONCE safely!
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. ALTER EXISTING TABLES TO ADD MISSING COLUMNS (SAFE & PRESERVES DATA)
-- ------------------------------------------------------------------------------

-- 1.1 accused_persons: Identity resolution, government identifiers & provenance
ALTER TABLE public.accused_persons ADD COLUMN IF NOT EXISTS date_of_birth TEXT;
ALTER TABLE public.accused_persons ADD COLUMN IF NOT EXISTS alias_names JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.accused_persons ADD COLUMN IF NOT EXISTS prison_inmate_no TEXT;
ALTER TABLE public.accused_persons ADD COLUMN IF NOT EXISTS cctns_person_id TEXT;
ALTER TABLE public.accused_persons ADD COLUMN IF NOT EXISTS aadhaar_hash TEXT;
ALTER TABLE public.accused_persons ADD COLUMN IF NOT EXISTS voter_id_masked TEXT;
ALTER TABLE public.accused_persons ADD COLUMN IF NOT EXISTS source_system TEXT DEFAULT 'Nyaya Mitra Case Index';
ALTER TABLE public.accused_persons ADD COLUMN IF NOT EXISTS source_record_id TEXT;
ALTER TABLE public.accused_persons ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());

CREATE INDEX IF NOT EXISTS idx_accused_inmate_no ON public.accused_persons(prison_inmate_no);
CREATE INDEX IF NOT EXISTS idx_accused_cctns ON public.accused_persons(cctns_person_id);
CREATE INDEX IF NOT EXISTS idx_accused_aadhaar ON public.accused_persons(aadhaar_hash);

-- 1.2 uploaded_documents: Security scanning, document lifecycle & audience controls
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

CREATE INDEX IF NOT EXISTS idx_uploaded_doc_status ON public.uploaded_documents(document_status);
CREATE INDEX IF NOT EXISTS idx_uploaded_doc_authority ON public.uploaded_documents(source_authority);

-- 1.3 audit_events: Cryptographic hash chain, sequence number & severity
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS event_hash TEXT;
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS previous_event_hash TEXT;
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS hash_algorithm TEXT DEFAULT 'SHA-256';
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS sequence_number BIGINT DEFAULT 0;
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS severity TEXT DEFAULT 'INFO';
ALTER TABLE public.audit_events ADD COLUMN IF NOT EXISTS data_status TEXT DEFAULT 'REAL';

CREATE INDEX IF NOT EXISTS idx_audit_events_event_hash ON public.audit_events(event_hash);
CREATE INDEX IF NOT EXISTS idx_audit_events_seq ON public.audit_events(sequence_number);
CREATE INDEX IF NOT EXISTS idx_audit_events_severity ON public.audit_events(severity);

-- 1.4 notifications: Role-targeted routing and recipient user ID
ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS target_role TEXT DEFAULT 'ALL';
ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS user_id TEXT;

CREATE INDEX IF NOT EXISTS idx_notifications_target_role ON public.notifications(target_role);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON public.notifications(user_id);

-- 1.5 court_cases & firs: Police station foreign key support
ALTER TABLE public.court_cases ADD COLUMN IF NOT EXISTS police_station_id TEXT;
CREATE INDEX IF NOT EXISTS idx_court_cases_station_id ON public.court_cases(police_station_id);

ALTER TABLE public.firs ADD COLUMN IF NOT EXISTS police_station_id TEXT;
CREATE INDEX IF NOT EXISTS idx_firs_station_id ON public.firs(police_station_id);

-- 1.6 cases: Optimistic locking version
ALTER TABLE public.cases ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;

-- 1.7 organization_users: Bar council reg number, phone & relationship
ALTER TABLE public.organization_users ADD COLUMN IF NOT EXISTS bar_registration_no TEXT;
ALTER TABLE public.organization_users ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE public.organization_users ADD COLUMN IF NOT EXISTS relationship_to_accused TEXT;
ALTER TABLE public.organization_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now());


-- ------------------------------------------------------------------------------
-- 2. RECREATE STAGE 8 & STAGE 9 WORKFLOW & RULES TABLES (CLEAN SLATE)
-- ------------------------------------------------------------------------------

-- Drop any previous outdated stubs to prevent "column does not exist" errors
DROP TABLE IF EXISTS public.legal_rule_audit_trail CASCADE;
DROP TABLE IF EXISTS public.legal_rule_executions CASCADE;
DROP TABLE IF EXISTS public.legal_rule_versions CASCADE;
DROP TABLE IF EXISTS public.legal_rules CASCADE;
DROP TABLE IF EXISTS public.matter_handoffs CASCADE;
DROP TABLE IF EXISTS public.matter_approvals CASCADE;
DROP TABLE IF EXISTS public.matter_artifact_versions CASCADE;
DROP TABLE IF EXISTS public.matter_approval_policies CASCADE;

-- 2.1 Deterministic Legal Rules (Statutory Rules Knowledge Base)
CREATE TABLE public.legal_rules (
    id TEXT PRIMARY KEY,
    rule_version TEXT NOT NULL,
    title TEXT NOT NULL,
    jurisdiction TEXT NOT NULL DEFAULT 'India / National',
    category TEXT NOT NULL,
    statutory_source TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL DEFAULT 'ACTIVE',
    applicability_conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
    required_inputs JSONB NOT NULL DEFAULT '[]'::jsonb,
    calculation_method TEXT NOT NULL,
    exclusions_and_provisos JSONB NOT NULL DEFAULT '[]'::jsonb,
    output_statuses JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation_template TEXT NOT NULL,
    legal_review_metadata JSONB DEFAULT '{}'::jsonb,
    approval_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE INDEX idx_legal_rules_category ON public.legal_rules(category);
CREATE INDEX idx_legal_rules_state ON public.legal_rules(lifecycle_state);

-- 2.2 Legal Rule Versions (Immutable version snapshots)
CREATE TABLE public.legal_rule_versions (
    id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL REFERENCES public.legal_rules(id) ON DELETE CASCADE,
    version_tag TEXT NOT NULL,
    rule_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    created_by TEXT
);

CREATE INDEX idx_legal_rule_versions_rule_id ON public.legal_rule_versions(rule_id);

-- 2.3 Legal Rule Executions (Deterministic statutory calculation audit log)
CREATE TABLE public.legal_rule_executions (
    id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    case_id TEXT NOT NULL,
    input_snapshot JSONB NOT NULL,
    input_provenance JSONB DEFAULT '{}'::jsonb,
    machine_status TEXT NOT NULL,
    explanation_json JSONB NOT NULL,
    executed_by TEXT,
    executed_role TEXT,
    execution_timestamp TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE INDEX idx_legal_rule_exec_case ON public.legal_rule_executions(case_id);
CREATE INDEX idx_legal_rule_exec_rule ON public.legal_rule_executions(rule_id);
CREATE INDEX idx_legal_rule_exec_ts ON public.legal_rule_executions(execution_timestamp DESC);

-- 2.4 Legal Rule Audit Trail (Rule change governance log)
CREATE TABLE public.legal_rule_audit_trail (
    id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    action TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    notes TEXT,
    timestamp TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE INDEX idx_legal_rule_audit_rule_id ON public.legal_rule_audit_trail(rule_id);
CREATE INDEX idx_legal_rule_audit_ts ON public.legal_rule_audit_trail(timestamp DESC);

-- 2.5 Matter Approval Policies (Four-eyes policy rules)
CREATE TABLE public.matter_approval_policies (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    required_levels INTEGER NOT NULL DEFAULT 1,
    requires_supervisor BOOLEAN NOT NULL DEFAULT false,
    authorized_roles_json JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE INDEX idx_matter_approval_pol_org_action ON public.matter_approval_policies(organization_id, action_type);

-- 2.6 Matter Approvals (Sign-offs, reviews & legal authorizations)
CREATE TABLE public.matter_approvals (
    approval_id TEXT PRIMARY KEY,
    matter_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    organization_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    decided_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    artifact_id TEXT NOT NULL,
    artifact_version_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    decision TEXT NOT NULL,
    comment TEXT,
    approval_level INTEGER NOT NULL DEFAULT 1,
    required_level INTEGER NOT NULL DEFAULT 1,
    supersedes_approval_id TEXT,
    is_valid BOOLEAN DEFAULT true,
    metadata_json JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_matter_approvals_matter ON public.matter_approvals(matter_id);
CREATE INDEX idx_matter_approvals_actor ON public.matter_approvals(actor_id);
CREATE INDEX idx_matter_approvals_created ON public.matter_approvals(created_at DESC);

-- 2.7 Matter Artifact Versions (Cryptographic document/petition draft versions)
CREATE TABLE public.matter_artifact_versions (
    version_id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    matter_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    version_tag TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    content_text TEXT NOT NULL,
    is_ai_generated BOOLEAN NOT NULL DEFAULT false,
    ai_model_name TEXT,
    provenance_tag TEXT DEFAULT 'HUMAN_AUTHORED',
    created_by TEXT NOT NULL,
    created_by_role TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_artifact_versions_matter ON public.matter_artifact_versions(matter_id);
CREATE INDEX idx_artifact_versions_artifact ON public.matter_artifact_versions(artifact_id, version_number);

-- 2.8 Matter Handoffs (Counsel reassignments and institutional transfers)
CREATE TABLE public.matter_handoffs (
    handoff_id TEXT PRIMARY KEY,
    matter_id TEXT NOT NULL,
    from_user_id TEXT NOT NULL,
    to_user_id TEXT NOT NULL,
    from_role TEXT NOT NULL,
    to_role TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    initiated_by TEXT NOT NULL,
    acknowledged_at TIMESTAMPTZ,
    metadata_json JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_matter_handoffs_matter ON public.matter_handoffs(matter_id);
CREATE INDEX idx_matter_handoffs_to_user ON public.matter_handoffs(to_user_id);


-- ------------------------------------------------------------------------------
-- 3. ENABLE ROW LEVEL SECURITY (RLS) & PUBLIC READ POLICIES
-- ------------------------------------------------------------------------------

ALTER TABLE public.legal_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.legal_rule_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.legal_rule_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.legal_rule_audit_trail ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matter_approval_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matter_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matter_artifact_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matter_handoffs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    CREATE POLICY "Allow access to legal_rules" ON public.legal_rules FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Allow access to legal_rule_versions" ON public.legal_rule_versions FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Allow access to legal_rule_executions" ON public.legal_rule_executions FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Allow access to legal_rule_audit_trail" ON public.legal_rule_audit_trail FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Allow access to matter_approval_policies" ON public.matter_approval_policies FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Allow access to matter_approvals" ON public.matter_approvals FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Allow access to matter_artifact_versions" ON public.matter_artifact_versions FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Allow access to matter_handoffs" ON public.matter_handoffs FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;


-- ------------------------------------------------------------------------------
-- 4. SEED ESSENTIAL STATUTORY DATA & POLICIES
-- ------------------------------------------------------------------------------

-- 4.1 Statutory Legal Rules Engine Rules
INSERT INTO public.legal_rules (
    id, rule_version, title, jurisdiction, category, statutory_source, effective_date,
    lifecycle_state, applicability_conditions, required_inputs, calculation_method,
    exclusions_and_provisos, output_statuses, explanation_template, legal_review_metadata, approval_metadata
) VALUES
(
    'RULE-BNSS-479-THRESHOLD-V1',
    'BNSS_479_RULESET_V1_2023',
    'BNSS Section 479 Undertrial Detention Statutory Rule',
    'India / National',
    'UNDERTRIAL_DETENTION_THRESHOLD',
    'Bharatiya Nagarik Suraksha Sanhita, 2023 (Section 479)',
    '2024-07-01',
    'ACTIVE',
    '{"min_imprisonment_days": 1, "is_capital_offence": false, "legal_code": "BNSS_2023"}'::jsonb,
    '["countable_custody_days", "max_imprisonment_days", "is_first_time_offender", "has_multiple_pending_cases"]'::jsonb,
    'BNSS_SECTION_479_STATUTORY_CALCULATION',
    '["Capital offences (death penalty) excluded", "Offences punishable with life imprisonment excluded", "Multiple pending cases proviso under Section 479(2)"]'::jsonb,
    '["ELIGIBLE_FIRST_TIME_ONE_THIRD", "ELIGIBLE_ONE_HALF", "NOT_ELIGIBLE_BELOW_THRESHOLD", "STATUTORILY_EXCLUDED"]'::jsonb,
    'Statutory evaluation under Section 479 BNSS: Undertrial has served {countable_days} countable days against statutory threshold of {threshold_days} days ({threshold_fraction}). Status: {status}.',
    '{"reviewed_by": "NALSA Technical Directorate", "review_date": "2024-07-01", "citation": "Act No. 46 of 2023"}'::jsonb,
    '{"approved_by": "National Legal Services Authority", "approval_status": "GAZETTED"}'::jsonb
),
(
    'RULE-CRPC-436A-THRESHOLD-V1',
    'CRPC_436A_RULESET_V1_1973',
    'CrPC Section 436A Undertrial Detention Rule (Pre-July 2024)',
    'India / National',
    'UNDERTRIAL_DETENTION_THRESHOLD',
    'Code of Criminal Procedure, 1973 (Section 436A)',
    '1974-04-01',
    'ACTIVE',
    '{"min_imprisonment_days": 1, "is_capital_offence": false, "legal_code": "CRPC_1973"}'::jsonb,
    '["countable_custody_days", "max_imprisonment_days"]'::jsonb,
    'CRPC_SECTION_436A_STATUTORY_CALCULATION',
    '["Capital offences excluded", "Discretionary extension on public prosecutor application"]'::jsonb,
    '["ELIGIBLE_ONE_HALF", "NOT_ELIGIBLE_BELOW_THRESHOLD", "STATUTORILY_EXCLUDED"]'::jsonb,
    'Statutory evaluation under Section 436A CrPC: Undertrial has served {countable_days} countable days against one-half statutory threshold of {threshold_days} days. Status: {status}.',
    '{"reviewed_by": "NALSA Advisory Committee", "review_date": "2023-01-15"}'::jsonb,
    '{"approved_by": "Ministry of Law and Justice", "approval_status": "HISTORIC_ACTIVE"}'::jsonb
)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    lifecycle_state = EXCLUDED.lifecycle_state,
    applicability_conditions = EXCLUDED.applicability_conditions,
    calculation_method = EXCLUDED.calculation_method,
    updated_at = timezone('utc'::text, now());

-- 4.2 Default Four-Eyes Approval Policies
INSERT INTO public.matter_approval_policies (
    id, organization_id, action_type, required_levels, requires_supervisor, authorized_roles_json
) VALUES
('policy_legal_filing_default', '*', 'LEGAL_FILING', 2, true, '["DEFENSE_ADVOCATE", "SUPERVISING_LEGAL_OFFICER", "DLSA_OFFICER"]'::jsonb),
('policy_counsel_assign_default', '*', 'COUNSEL_ASSIGNMENT', 1, false, '["DLSA_OFFICER", "SUPERVISING_LEGAL_OFFICER", "PLATFORM_ADMIN"]'::jsonb),
('policy_bail_draft_default', '*', 'BAIL_DRAFT_GENERATE', 1, false, '["DEFENSE_ADVOCATE", "DLSA_OFFICER", "SUPERVISING_LEGAL_OFFICER"]'::jsonb)
ON CONFLICT (id) DO UPDATE SET
    required_levels = EXCLUDED.required_levels,
    requires_supervisor = EXCLUDED.requires_supervisor,
    authorized_roles_json = EXCLUDED.authorized_roles_json,
    updated_at = timezone('utc'::text, now());

-- 4.3 Update Demo Users with bar registration numbers & phone contacts
UPDATE public.organization_users SET
    bar_registration_no = CASE
        WHEN id = 'demo_advocate' THEN 'D/1042/2014'
        WHEN id = 'demo_supervising' THEN 'D/0882/2010'
        ELSE bar_registration_no
    END,
    phone = CASE
        WHEN id = 'demo_advocate' THEN '+91 98112 04512'
        WHEN id = 'demo_supervising' THEN '+91 98110 33419'
        WHEN id = 'demo_dlsa' THEN '+91 98101 22934'
        WHEN id = 'demo_jail' THEN '+91 98100 11223'
        WHEN id = 'demo_police' THEN '+91 98104 55667'
        WHEN id = 'demo_accused' THEN '+91 98711 66778'
        WHEN id = 'demo_family' THEN '+91 98711 99001'
        ELSE phone
    END,
    updated_at = timezone('utc'::text, now())
WHERE id IN ('demo_advocate', 'demo_supervising', 'demo_dlsa', 'demo_jail', 'demo_police', 'demo_accused', 'demo_family');

-- ------------------------------------------------------------------------------
-- 5. REFRESH SCHEMA CACHE
-- ------------------------------------------------------------------------------
NOTIFY pgrst, 'reload schema';

SELECT 
    'All missing tables, columns, indexes, policies, and seeds successfully synced to Supabase!' AS migration_result,
    timezone('utc'::text, now()) AS completed_at;

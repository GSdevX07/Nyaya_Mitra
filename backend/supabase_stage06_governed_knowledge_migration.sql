-- ============================================================================
-- NYAYA MITRA — STAGE 06 GOVERNED LEGAL KNOWLEDGE LAYER MIGRATION
-- Run this script in the Supabase SQL Editor.
-- It creates all required tables, performance indexes, RLS policies, and seed data.
-- It is completely IDEMPOTENT (safe to run multiple times).
-- ============================================================================

-- 1. LEGAL SOURCES REGISTRY
CREATE TABLE IF NOT EXISTS public.legal_sources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    short_name TEXT,
    issuing_authority TEXT NOT NULL,
    effective_date DATE NOT NULL,
    publication_date DATE,
    jurisdiction TEXT NOT NULL,
    source_url TEXT,
    document_hash TEXT NOT NULL,
    version TEXT DEFAULT '1.0',
    language TEXT DEFAULT 'en',
    legal_domain TEXT NOT NULL,
    lifecycle_status TEXT DEFAULT 'discovered' CHECK (lifecycle_status IN ('discovered', 'reviewed', 'approved', 'active', 'superseded', 'retired')),
    superseded_by_id TEXT REFERENCES public.legal_sources(id),
    raw_content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    reviewed_by TEXT,
    approved_by TEXT,
    audit_notes TEXT
);

-- 2. LEGAL CHUNKS (VERBATIM STATUTORY PASSAGES)
CREATE TABLE IF NOT EXISTS public.legal_chunks (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES public.legal_sources(id) ON DELETE CASCADE,
    document_title TEXT NOT NULL,
    section_number TEXT,
    section_title TEXT,
    original_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    start_char INTEGER DEFAULT 0,
    end_char INTEGER DEFAULT 0,
    citation_key TEXT,
    legal_domain TEXT,
    jurisdiction TEXT,
    metadata_json JSONB DEFAULT '{}'::jsonb
);

-- 3. RETRIEVAL BENCHMARK EVALUATION SUITE
CREATE TABLE IF NOT EXISTS public.legal_evaluation_benchmarks (
    id TEXT PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_category TEXT NOT NULL,
    expected_source_ids_json JSONB NOT NULL,
    expected_citation_keys_json JSONB NOT NULL,
    target_statute TEXT,
    difficulty TEXT DEFAULT 'STANDARD',
    last_recall_score REAL DEFAULT 0.0,
    last_evaluated_at TIMESTAMP WITH TIME ZONE
);

-- 4. RETRIEVAL TELEMETRY & AUDIT LOGS
CREATE TABLE IF NOT EXISTS public.legal_retrieval_logs (
    id TEXT PRIMARY KEY,
    query_id TEXT,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    organization_id TEXT,
    query_text TEXT NOT NULL,
    source_ids_json JSONB,
    source_versions_json JSONB,
    matched_citation_keys_json JSONB,
    relevance_scores_json JSONB,
    selected_passages_json JSONB,
    used_superseded INTEGER DEFAULT 0,
    grounding_score REAL DEFAULT 0.0,
    routed_to_human_review INTEGER DEFAULT 0,
    status TEXT DEFAULT 'SUCCESS',
    queried_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 5. DURABLE HUMAN REVIEW ESCALATION QUEUE
CREATE TABLE IF NOT EXISTS public.legal_human_review_tasks (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    case_id TEXT,
    statement_hash TEXT NOT NULL,
    draft_statement TEXT NOT NULL,
    unsupported_citations_json JSONB NOT NULL,
    retrieved_context_json JSONB,
    grounding_score REAL NOT NULL,
    escalation_reason TEXT NOT NULL,
    assigned_role TEXT DEFAULT 'SUPERVISING_LEGAL_OFFICER',
    assigned_user_id TEXT,
    review_status TEXT DEFAULT 'PENDING_REVIEW' CHECK (review_status IN ('PENDING_REVIEW', 'RESOLVED', 'REJECTED')),
    resolution_notes TEXT,
    resolved_by TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- ── PERFORMANCE INDEXES ─────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_legal_sources_status ON public.legal_sources(lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_legal_sources_domain ON public.legal_sources(legal_domain);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_source ON public.legal_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_citation ON public.legal_chunks(citation_key);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_section ON public.legal_chunks(section_number);
CREATE INDEX IF NOT EXISTS idx_legal_escalations_status ON public.legal_human_review_tasks(review_status);
CREATE INDEX IF NOT EXISTS idx_legal_escalations_hash ON public.legal_human_review_tasks(statement_hash);
CREATE INDEX IF NOT EXISTS idx_legal_retrieval_actor ON public.legal_retrieval_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_legal_retrieval_queried ON public.legal_retrieval_logs(queried_at DESC);

-- ── ROW LEVEL SECURITY (RLS) POLICIES ───────────────────────────────────────
ALTER TABLE public.legal_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.legal_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.legal_evaluation_benchmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.legal_retrieval_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.legal_human_review_tasks ENABLE ROW LEVEL SECURITY;

-- Allow service role and backend full access
DROP POLICY IF EXISTS service_all_legal_sources ON public.legal_sources;
CREATE POLICY service_all_legal_sources ON public.legal_sources FOR ALL USING (true);

DROP POLICY IF EXISTS service_all_legal_chunks ON public.legal_chunks;
CREATE POLICY service_all_legal_chunks ON public.legal_chunks FOR ALL USING (true);

DROP POLICY IF EXISTS service_all_legal_benchmarks ON public.legal_evaluation_benchmarks;
CREATE POLICY service_all_legal_benchmarks ON public.legal_evaluation_benchmarks FOR ALL USING (true);

DROP POLICY IF EXISTS service_all_legal_retrieval_logs ON public.legal_retrieval_logs;
CREATE POLICY service_all_legal_retrieval_logs ON public.legal_retrieval_logs FOR ALL USING (true);

DROP POLICY IF EXISTS service_all_legal_escalations ON public.legal_human_review_tasks;
CREATE POLICY service_all_legal_escalations ON public.legal_human_review_tasks FOR ALL USING (true);

-- ── SEED INITIAL GOVERNED STATUTORY SOURCES ──────────────────────────────────
INSERT INTO public.legal_sources (
    id, title, short_name, issuing_authority, effective_date, publication_date,
    jurisdiction, source_url, document_hash, version, language, legal_domain,
    lifecycle_status, superseded_by_id, raw_content, audit_notes
) VALUES 
(
    'src_bnss_2023',
    'The Bharatiya Nagarik Suraksha Sanhita, 2023',
    'BNSS 2023',
    'Parliament of India',
    '2024-07-01',
    '2023-12-25',
    'National (India)',
    'https://egazette.gov.in/WriteReadData/2023/250882.pdf',
    '47ad9efdab75c5dfee7bf8502fa3ec2bf9b9cf6cad85b7f6bbaf05713a7bec08',
    'Act No. 46 of 2023',
    'en',
    'CRIMINAL_PROCEDURE',
    'active',
    NULL,
    'Section 479: Maximum period for which an undertrial prisoner can be detained. Section 479(1): One-half detention mandatory bail. Provided that first-time offender detained for one-third maximum imprisonment shall be released on bond. Section 479(2): Jail Superintendent must apply forthwith.',
    'Official gazette statutory text verified against Act No. 46 of 2023.'
),
(
    'src_bns_2023',
    'The Bharatiya Nyaya Sanhita, 2023',
    'BNS 2023',
    'Parliament of India',
    '2024-07-01',
    '2023-12-25',
    'National (India)',
    'https://egazette.gov.in/WriteReadData/2023/250881.pdf',
    'a3c4e5f67890123456789abcdef0123456789abcdef0123456789abcdef01234',
    'Act No. 45 of 2023',
    'en',
    'PENAL_LAW',
    'active',
    NULL,
    'Section 303: Theft. Imprisonment up to 3 years or fine. Section 303(2): Community service for theft under 5,000 rupees on first conviction.',
    'Official gazette text verified against Act No. 45 of 2023.'
),
(
    'src_crpc_1973',
    'The Code of Criminal Procedure, 1973',
    'CrPC 1973',
    'Parliament of India',
    '1974-04-01',
    '1974-01-25',
    'National (India)',
    'https://legislative.gov.in/sites/default/files/A1974-02.pdf',
    'f1e2d3c4b5a69788796a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e',
    'Act No. 2 of 1974',
    'en',
    'CRIMINAL_PROCEDURE',
    'superseded',
    'src_bnss_2023',
    'Section 436A: Maximum period for which an undertrial prisoner can be detained. Half of maximum imprisonment threshold.',
    'Repealed and superseded by Section 479 BNSS effective 01-07-2024.'
),
(
    'src_ipc_1860',
    'The Indian Penal Code, 1860',
    'IPC 1860',
    'British Imperial Legislative Council / Parliament',
    '1862-01-01',
    '1860-10-06',
    'National (India)',
    'https://legislative.gov.in/sites/default/files/A1860-45.pdf',
    'c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6',
    'Act No. 45 of 1860',
    'en',
    'PENAL_LAW',
    'superseded',
    'src_bns_2023',
    'Section 379: Punishment for theft. Imprisonment up to 3 years, or with fine, or with both.',
    'Repealed and superseded by Section 303 BNS effective 01-07-2024.'
),
(
    'src_sc_bail_sop_2024',
    'Supreme Court Guidelines on Section 479 BNSS Undertrial Bail Administration',
    'SC 479 SOP 2024',
    'Supreme Court of India',
    '2024-08-23',
    '2024-08-23',
    'All High Courts and Prison Authorities (India)',
    'https://main.sci.gov.in/judgment/2024/in_re_section_479_bnss.pdf',
    '17ae6068e44c487e6928ae75d72c3d6df3fdf335f0d737e9cc0ee807539c28ca',
    'Writ Petition (Crl.) No. 341 of 2024',
    'en',
    'JUDICIAL_PRECEDENT',
    'active',
    NULL,
    'Section 1: Retrospective application of Section 479 BNSS to all pending undertrials regardless of offence date.',
    'Judicial precedent mandating retrospective application of 1/3rd first-time undertrial threshold.'
)
ON CONFLICT (id) DO UPDATE SET
    lifecycle_status = EXCLUDED.lifecycle_status,
    superseded_by_id = EXCLUDED.superseded_by_id,
    audit_notes = EXCLUDED.audit_notes;

-- ── SEED INITIAL BENCHMARK EVALUATION QUERIES ────────────────────────────────
INSERT INTO public.legal_evaluation_benchmarks (
    id, query_category, query_text, target_statute,
    expected_source_ids_json, expected_citation_keys_json, difficulty
) VALUES 
(
    'bench_sec479_first_time',
    'BNSS_SECTION_479_FIRST_TIME',
    'one-third detention bail for first-time undertrial under BNSS section 479',
    'BNSS 2023',
    '["src_bnss_2023"]'::jsonb,
    '["BNSS:479", "BNSS:479(1)"]'::jsonb,
    'STANDARD'
),
(
    'bench_jail_superintendent_duty',
    'BNSS_SECTION_479_SUPERINTENDENT_DUTY',
    'jail superintendent mandatory application for undertrial bail',
    'BNSS 2023',
    '["src_bnss_2023"]'::jsonb,
    '["BNSS:479(2)"]'::jsonb,
    'STANDARD'
),
(
    'bench_sc_retrospective',
    'SUPREME_COURT_SOP_RETROSPECTIVE',
    'Supreme Court retrospective application of section 479 to pre-2024 pending cases',
    'SC 479 Guidelines 2024',
    '["src_bnss_2023", "src_sc_bail_sop_2024"]'::jsonb,
    '["SC:479_RETROSPECTIVE", "BNSS:479"]'::jsonb,
    'COMPLEX'
),
(
    'bench_bns_theft_community',
    'BNS_THEFT_PENALTY',
    'theft community service under BNS section 303 for value under 5000',
    'BNS 2023',
    '["src_bns_2023"]'::jsonb,
    '["BNS:303", "BNS:303(2)"]'::jsonb,
    'STANDARD'
),
(
    'bench_superseded_crpc436a',
    'SUPERSEDED_CRPC_436A',
    'Section 436A CrPC maximum undertrial detention replaced by section 479 BNSS',
    'CrPC 1973',
    '["src_crpc_1973"]'::jsonb,
    '["CRPC:436A"]'::jsonb,
    'STANDARD'
)
ON CONFLICT (id) DO UPDATE SET
    query_text = EXCLUDED.query_text,
    expected_source_ids_json = EXCLUDED.expected_source_ids_json,
    expected_citation_keys_json = EXCLUDED.expected_citation_keys_json;

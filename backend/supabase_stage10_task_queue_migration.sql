-- ============================================================================
-- NYAYA MITRA — STAGE 10 AUTHORITY OPERATIONS WORKBENCH MIGRATION
-- Task Queue & Legal Aid Panel Advocates Tables for Supabase PostgreSQL
-- ============================================================================

-- 1. TASK QUEUE TABLE
CREATE TABLE IF NOT EXISTS public.task_queue (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    accused_name TEXT,
    task_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    owner_role TEXT NOT NULL,
    owner_user_id TEXT,
    owner_name TEXT,
    priority TEXT NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    due_date TEXT NOT NULL,
    source TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_APPROVAL', 'COMPLETED', 'ESCALATED', 'CANCELLED')),
    escalation_path TEXT NOT NULL,
    facility TEXT,
    district TEXT,
    custody_duration_days INTEGER DEFAULT 0,
    document_completeness_pct INTEGER DEFAULT 100,
    has_data_conflict INTEGER DEFAULT 0,
    legal_aid_need INTEGER DEFAULT 0,
    assignment_status TEXT DEFAULT 'AVAILABLE',
    matter_status TEXT DEFAULT 'INTAKE',
    hearing_date TEXT,
    is_consequential INTEGER DEFAULT 0,
    metadata_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    completed_at TIMESTAMP WITH TIME ZONE,
    completed_by TEXT
);

-- Performance Indexes for Task Queue
CREATE INDEX IF NOT EXISTS idx_task_queue_owner_role ON public.task_queue(owner_role);
CREATE INDEX IF NOT EXISTS idx_task_queue_case_id ON public.task_queue(case_id);
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON public.task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_facility ON public.task_queue(facility);
CREATE INDEX IF NOT EXISTS idx_task_queue_district ON public.task_queue(district);
CREATE INDEX IF NOT EXISTS idx_task_queue_due_date ON public.task_queue(due_date);
CREATE INDEX IF NOT EXISTS idx_task_queue_priority ON public.task_queue(priority);

-- 2. LEGAL AID PANEL ADVOCATES TABLE (IF NOT EXISTS)
CREATE TABLE IF NOT EXISTS public.legal_aid_panel_advocates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    bar_council_id TEXT NOT NULL UNIQUE,
    designation TEXT DEFAULT 'Panel Counsel',
    district TEXT NOT NULL,
    state TEXT DEFAULT 'Delhi',
    email TEXT,
    phone TEXT,
    active_cases INTEGER DEFAULT 0,
    max_active_cases INTEGER DEFAULT 15,
    panel_status TEXT DEFAULT 'ACTIVE' CHECK (panel_status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),
    experience_years INTEGER DEFAULT 5,
    specialization TEXT DEFAULT 'Criminal Defense & Bail',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_panel_advocates_district ON public.legal_aid_panel_advocates(district);
CREATE INDEX IF NOT EXISTS idx_panel_advocates_panel_status ON public.legal_aid_panel_advocates(panel_status);

-- 3. ENABLE ROW LEVEL SECURITY
ALTER TABLE public.task_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.legal_aid_panel_advocates ENABLE ROW LEVEL SECURITY;

-- Allow institutional users access to operations task queue
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'task_queue' AND policyname = 'Institutional access to task queue'
    ) THEN
        CREATE POLICY "Institutional access to task queue"
            ON public.task_queue
            FOR ALL
            TO authenticated, anon
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;

-- Allow read access to panel advocates roster
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'legal_aid_panel_advocates' AND policyname = 'Institutional read access to panel advocates'
    ) THEN
        CREATE POLICY "Institutional read access to panel advocates"
            ON public.legal_aid_panel_advocates
            FOR ALL
            TO authenticated, anon
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;

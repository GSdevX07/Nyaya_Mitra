-- ==============================================================================
-- Nyaya Mitra: Supabase Audit Events data_status Migration
-- Adds data_status column to audit_events to align with SQLite audit ledger.
-- ==============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'audit_events'
          AND column_name = 'data_status'
    ) THEN
        ALTER TABLE public.audit_events ADD COLUMN data_status TEXT DEFAULT 'REAL';
        RAISE NOTICE 'Added data_status column to public.audit_events';
    ELSE
        RAISE NOTICE 'Column data_status already exists in public.audit_events';
    END IF;
END $$;

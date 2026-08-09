-- ============================================================
-- Nyaya Mitra: uploaded_documents table
-- Run this once in the Supabase SQL editor.
-- ============================================================

CREATE TABLE IF NOT EXISTS uploaded_documents (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           TEXT        NOT NULL,
    document_type     TEXT        NOT NULL,
    file_name         TEXT        NOT NULL,
    extracted_text    TEXT,                        -- OCR / PDF text output
    custom_text       TEXT,                        -- manually pasted text
    is_handwritten    BOOLEAN     NOT NULL DEFAULT FALSE,
    ocr_engine        TEXT,                        -- e.g. "Tesseract OCR", "pypdf text extraction"
    file_hash         TEXT,                        -- SHA-256 hex of raw file bytes
    file_size_bytes   INTEGER,
    mime_type         TEXT,
    uploaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast case-scoped lookups
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_case_id
    ON uploaded_documents (case_id);

-- Index for document type queries
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_doc_type
    ON uploaded_documents (document_type);

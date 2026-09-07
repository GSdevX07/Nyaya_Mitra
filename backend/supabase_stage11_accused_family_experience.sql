-- =============================================================================
-- Nyaya Mitra: Stage 11 Migration — Accused & Family Experience
-- Tables for Citizen Action Requests, Notification Preferences, and Consent Records
-- =============================================================================

-- 1. Citizen Action Requests (Structured Help, Discrepancy Flags, Copy Requests)
CREATE TABLE IF NOT EXISTS citizen_action_requests (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    accused_id TEXT NOT NULL,
    request_type TEXT NOT NULL, -- REQUEST_HELP, FLAG_INCORRECT_INFO, REQUEST_DOCUMENT_COPY, REQUEST_DLSA_CONTACT
    requested_by_user_id TEXT NOT NULL,
    requested_by_role TEXT NOT NULL, -- ACCUSED_USER, FAMILY_GUARDIAN
    subject TEXT NOT NULL,
    details TEXT NOT NULL,
    target_document_type TEXT,
    discrepancy_field TEXT,
    status TEXT DEFAULT 'SUBMITTED', -- SUBMITTED, IN_REVIEW, ACTION_TAKEN, RESOLVED, CLOSED
    response_notes TEXT,
    assigned_officer_id TEXT,
    task_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_citizen_req_case_id ON citizen_action_requests(case_id);
CREATE INDEX IF NOT EXISTS idx_citizen_req_user_id ON citizen_action_requests(requested_by_user_id);
CREATE INDEX IF NOT EXISTS idx_citizen_req_status ON citizen_action_requests(status);

-- 2. Citizen Notification Preferences & Statutory Consent Record
CREATE TABLE IF NOT EXISTS citizen_notification_preferences (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    phone_number TEXT,
    channel_sms_enabled BOOLEAN DEFAULT TRUE,
    channel_whatsapp_enabled BOOLEAN DEFAULT TRUE,
    channel_in_app_enabled BOOLEAN DEFAULT TRUE,
    preferred_language TEXT DEFAULT 'en',
    consent_status TEXT DEFAULT 'OPTED_IN', -- OPTED_IN, OPTED_OUT
    consent_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    consent_version TEXT DEFAULT 'v1.0-statutory-notice',
    consent_text TEXT DEFAULT 'I consent to receive case status updates and legal-aid notices under the Legal Services Authorities Act, 1987.',
    consent_ip TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_citizen_pref_case_id ON citizen_notification_preferences(case_id);

-- 3. Citizen Notification Dispatch Logs (Simulated & Live Carrier Audits)
CREATE TABLE IF NOT EXISTS citizen_notification_logs (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    channel TEXT NOT NULL, -- SMS, WHATSAPP, IN_APP
    recipient TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'SIMULATED_DISPATCHED', -- QUEUED, SIMULATED_DISPATCHED, DELIVERED, FAILED
    dispatch_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_citizen_notif_logs_case ON citizen_notification_logs(case_id);

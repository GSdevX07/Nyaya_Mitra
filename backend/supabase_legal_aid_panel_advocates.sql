-- ============================================================================
-- Supabase Migration: Legal Aid Panel Advocates & LADC Counsel
-- Fixes: ERROR 42P01: relation "legal_aid_panel_advocates" does not exist
-- ============================================================================

CREATE TABLE IF NOT EXISTS legal_aid_panel_advocates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    bar_registration_no TEXT,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    dlsa_institution TEXT NOT NULL,
    panel_type TEXT NOT NULL,
    matter_type TEXT NOT NULL DEFAULT 'Criminal / Undertrial',
    panel_status TEXT NOT NULL DEFAULT 'Active',
    active_cases INTEGER DEFAULT 0,
    experience_years INTEGER DEFAULT 5,
    court_jurisdiction TEXT,
    is_higher_level_panel INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices for rapid filtering
CREATE INDEX IF NOT EXISTS idx_panel_advocates_district ON legal_aid_panel_advocates(district);
CREATE INDEX IF NOT EXISTS idx_panel_advocates_status ON legal_aid_panel_advocates(panel_status);
CREATE INDEX IF NOT EXISTS idx_panel_advocates_state ON legal_aid_panel_advocates(state);

-- Enable Row Level Security (RLS) if desired, with public read access
ALTER TABLE legal_aid_panel_advocates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read access to legal_aid_panel_advocates"
ON legal_aid_panel_advocates
FOR SELECT
TO authenticated, anon
USING (true);

-- Empanelled Legal Aid Defense Counsel (LADC) & DLSA Panel Advocates Seed
INSERT INTO legal_aid_panel_advocates (
    id, name, bar_registration_no, state, district, dlsa_institution,
    panel_type, matter_type, panel_status, active_cases, experience_years,
    court_jurisdiction, is_higher_level_panel
) VALUES
-- Bengaluru Urban
('adv_kar_blr_01', 'Adv. Arun Kumar', 'KAR/1420/2015', 'Karnataka', 'Bengaluru Urban', 'District Legal Services Authority, Bengaluru Urban', 'LADC Chief Defense Counsel', 'Criminal / Undertrial', 'Active', 3, 12, 'City Civil and Sessions Court, Bengaluru', 0),
('adv_kar_blr_02', 'Adv. Priya Sharma', 'KAR/2180/2018', 'Karnataka', 'Bengaluru Urban', 'District Legal Services Authority, Bengaluru Urban', 'LADC Deputy Defense Counsel', 'Criminal / Undertrial', 'Active', 2, 8, 'City Civil and Sessions Court, Bengaluru', 0),
('adv_kar_blr_03', 'Adv. Ravi Shankar', 'KAR/3341/2019', 'Karnataka', 'Bengaluru Urban', 'District Legal Services Authority, Bengaluru Urban', 'DLSA Panel Advocate', 'Criminal / Undertrial', 'Active', 4, 6, 'Chief Metropolitan Magistrate Court, Bengaluru', 0),
-- Karnataka SLSA / High Court Special Panel
('adv_kar_slsa_01', 'Adv. Kavitha Rao', 'KAR/0912/2011', 'Karnataka', 'Bengaluru Urban', 'Karnataka State Legal Services Authority (KSLSA)', 'High Court Legal Services Committee (HCLSC) Special Panel', 'Criminal / Undertrial', 'Active', 1, 15, 'High Court of Karnataka, Bengaluru', 1),
-- Secondary / Out-of-District Karnataka
('adv_kar_blr_other1', 'Adv. Suresh Gowda', 'KAR/4412/2017', 'Karnataka', 'Ballari', 'District Legal Services Authority, Ballari', 'DLSA Panel Advocate', 'Criminal / Undertrial', 'Active', 3, 9, 'District and Sessions Court, Ballari', 0),
('adv_kar_blr_other2', 'Adv. Manjunath K', 'KAR/5521/2016', 'Karnataka', 'Mysuru', 'District Legal Services Authority, Mysuru', 'DLSA Panel Advocate', 'Criminal / Undertrial', 'Active', 2, 10, 'District and Sessions Court, Mysuru', 0),
-- Central Delhi
('demo_advocate', 'Adv. Rajesh Sharma', 'D/1042/2014', 'Delhi', 'Central Delhi', 'District Legal Services Authority, Central Delhi', 'DLSA Senior Panel Counsel', 'Criminal / Undertrial', 'Active', 4, 12, 'Tis Hazari District Court Complex', 0),
('LWYR-002', 'Adv. Priya Verma', 'D/2180/2018', 'Delhi', 'Central Delhi', 'District Legal Services Authority, Central Delhi', 'LADC Deputy Defense Counsel', 'Criminal / Undertrial', 'Active', 2, 8, 'Tis Hazari District Court Complex', 0),
('LWYR-003', 'Adv. Amit Sen', 'D/0891/2016', 'Delhi', 'Central Delhi', 'District Legal Services Authority, Central Delhi', 'DLSA Panel Advocate', 'Criminal / Undertrial', 'Active', 3, 10, 'Tis Hazari District Court Complex', 0),
('LWYR-004', 'Adv. Meera Nair', 'D/3341/2019', 'Delhi', 'Central Delhi', 'Delhi State Legal Services Authority (DSLSA)', 'High Court Legal Services Committee (HCLSC) Special Panel', 'Criminal / Undertrial', 'Active', 1, 6, 'High Court of Delhi, New Delhi', 1),
('LWYR-005', 'Adv. Sanjay Gupta', 'D/0512/2012', 'Delhi', 'Central Delhi', 'District Legal Services Authority, Central Delhi', 'DLSA Senior Panel Counsel', 'Criminal / Undertrial', 'Active', 5, 14, 'Tis Hazari District Court Complex', 0),
-- Inactive Counsel (for status testing)
('adv_inactive_blr', 'Adv. Vikas Reddy', 'KAR/9999/2020', 'Karnataka', 'Bengaluru Urban', 'District Legal Services Authority, Bengaluru Urban', 'DLSA Panel Advocate', 'Criminal / Undertrial', 'Suspended', 0, 4, 'City Civil and Sessions Court, Bengaluru', 0)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    bar_registration_no = EXCLUDED.bar_registration_no,
    panel_type = EXCLUDED.panel_type,
    panel_status = EXCLUDED.panel_status,
    active_cases = EXCLUDED.active_cases,
    court_jurisdiction = EXCLUDED.court_jurisdiction;

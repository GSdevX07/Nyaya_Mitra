-- ============================================================================
-- NYAYA MITRA: Role-Specific Database-Driven Notifications Migration
-- Run this in your Supabase SQL Editor to enable role-based notification filtering
-- and seed role-specific notifications for all stakeholders.
-- ============================================================================

-- 1. Add target_role and user_id columns if they do not exist
ALTER TABLE IF EXISTS notifications 
  ADD COLUMN IF NOT EXISTS target_role TEXT DEFAULT 'ALL',
  ADD COLUMN IF NOT EXISTS user_id TEXT;

-- 2. Create index for high-performance role-based notification feeds
CREATE INDEX IF NOT EXISTS idx_notifications_target_role 
  ON notifications(target_role, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id 
  ON notifications(user_id, timestamp DESC);

-- 3. Update legacy rows so that sensitive alerts do not leak to unrelated roles
UPDATE notifications 
SET target_role = 'SUPERVISING_LEGAL_OFFICER,GOV_ADMIN' 
WHERE id LIKE 'notif_esc_%';

UPDATE notifications 
SET target_role = 'DLSA_OFFICER,DEFENSE_ADVOCATE' 
WHERE id LIKE 'NOTIF-UTP-%';

-- 4. Seed Role-Specific Notifications
INSERT INTO notifications (id, case_id, title, message, type, target_role, user_id, is_read, timestamp)
VALUES
  -- POLICE_OFFICER
  (
    'NOTIF-POLICE-01',
    'UTP-0001',
    'Remand Period Expiry Alert — Sec 187 BNSS',
    'Accused Suresh Kumar (FIR 204/2026, Crime Branch Delhi) initial 15-day police custody remand expires in 48 hours. File status report or transition to judicial custody.',
    'urgent',
    'POLICE_OFFICER',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-POLICE-02',
    'UTP-0015',
    'Pending Investigation Charge Sheet Deadline',
    'Charge Sheet for Case UTP-0015 (FIR 88/2026) due within 14 days under Section 193 BNSS to prevent default bail.',
    'warning',
    'POLICE_OFFICER',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-POLICE-03',
    'UTP-0007',
    'Production Warrant Notification',
    'Physical/VC Production Warrant issued by Chief Metropolitan Magistrate for Ramesh Kumar on 2026-09-08.',
    'info',
    'POLICE_OFFICER',
    NULL,
    FALSE,
    NOW()
  ),
  -- JAIL_OFFICER
  (
    'NOTIF-JAIL-01',
    'UTP-0007',
    'Section 479(2) BNSS Mandatory Bail Application Required',
    'Undertrial prisoner Ramesh Kumar (UTP-0007) has completed 1/3rd sentence duration as a first-time offender. Superintendent application to Court required forthwith.',
    'urgent',
    'JAIL_OFFICER',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-JAIL-02',
    'UTP-0001',
    'Nominal Roll & Custody Certificate Due',
    'High Court Registry requested verified Nominal Roll and custody conduct certificate for Suresh Kumar (UTP-0001) for upcoming bail hearing.',
    'warning',
    'JAIL_OFFICER',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-JAIL-03',
    'UTP-0007',
    'Medical Examination Review Pending',
    'Quarterly medical vulnerability review report for senior undertrial prisoner (UTP-0007, Age 63) awaiting Jail Medical Officer sign-off.',
    'info',
    'JAIL_OFFICER',
    NULL,
    FALSE,
    NOW()
  ),
  -- DEFENSE_ADVOCATE & CONTROLLED_EXTERNAL_ADVOCATE
  (
    'NOTIF-ADV-01',
    'UTP-0001',
    'Bail Application Draft Ready for Filing',
    'Consolidated BNSS Section 479 application package for Suresh Kumar (UTP-0001) generated and verified against 2024 Supreme Court SOP.',
    'success',
    'DEFENSE_ADVOCATE,CONTROLLED_EXTERNAL_ADVOCATE',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-ADV-02',
    'UTP-0007',
    'Client Eligibility Radar Alert',
    'New Section 479(1) Proviso 1 eligibility detected for Ramesh Kumar (UTP-0007, First-time offender threshold reached).',
    'urgent',
    'DEFENSE_ADVOCATE,CONTROLLED_EXTERNAL_ADVOCATE',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-ADV-03',
    'UTP-0001',
    'Court Hearing Scheduled',
    'Regular Bail Hearing scheduled before Additional Sessions Judge, Tis Hazari Courts on 2026-09-08 for Case UTP-0001.',
    'info',
    'DEFENSE_ADVOCATE,CONTROLLED_EXTERNAL_ADVOCATE',
    NULL,
    FALSE,
    NOW()
  ),
  -- DLSA_OFFICER
  (
    'NOTIF-DLSA-01',
    'UTP-0015',
    'Legal Aid Panel Assignment Pending',
    'Indigent undertrial prisoner (UTP-0015) has requested DLSA representation. Panel advocate assignment awaiting endorsement.',
    'warning',
    'DLSA_OFFICER',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-DLSA-02',
    'UTP-0007',
    'High Priority Bail Eligibility Flagged',
    'Alert [HIGH]: Case UTP-0007 (Ramesh Kumar) is legally eligible for bail under BNSS 479. Urgency Score: 266.',
    'urgent',
    'DLSA_OFFICER',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-DLSA-03',
    'UTP-0001',
    'Undertrial Review Committee (UTRC) Docket Updated',
    'Monthly UTRC review docket prepared with 4 candidates eligible for immediate release recommendations.',
    'info',
    'DLSA_OFFICER',
    NULL,
    FALSE,
    NOW()
  ),
  -- SUPERVISING_LEGAL_OFFICER & GOV_ADMIN
  (
    'NOTIF-SLSA-01',
    'UTP-0001',
    'Statutory Citation Integrity Escalation',
    'Unsupported legal claims detected in advocate filing draft. Routed to Supervising Legal Officer for human verification.',
    'urgent',
    'SUPERVISING_LEGAL_OFFICER,GOV_ADMIN',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-SLSA-02',
    'src_bnss_2023',
    'Discovered Legal Source Pending Approval',
    'New statutory enactment proposed by DLSA Officer is in discovered state awaiting formal supervisor review and promotion.',
    'warning',
    'SUPERVISING_LEGAL_OFFICER,GOV_ADMIN',
    NULL,
    FALSE,
    NOW()
  ),
  -- READ_ONLY_AUDITOR
  (
    'NOTIF-AUDIT-01',
    'UTP-0015',
    'Statutory Compliance Audit Alert',
    'Discrepancy detected in custody days computation between Police FIR arrest log and Prison intake register for UTP-0015.',
    'warning',
    'READ_ONLY_AUDITOR',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-AUDIT-02',
    NULL,
    'Benchmark Retrieval Suite Verified',
    'Stage 06 statutory retrieval benchmark evaluated: Recall@1 = 100%, MRR = 1.0 across all legal query categories.',
    'success',
    'READ_ONLY_AUDITOR',
    NULL,
    FALSE,
    NOW()
  ),
  -- ACCUSED_USER & FAMILY_GUARDIAN
  (
    'NOTIF-CITIZEN-01',
    'UTP-0001',
    'Bail Application Status Update',
    'Your legal aid counsel has submitted an application for bail under Section 479 BNSS. Hearing date set for 2026-09-08.',
    'success',
    'ACCUSED_USER,FAMILY_GUARDIAN',
    NULL,
    FALSE,
    NOW()
  ),
  (
    'NOTIF-CITIZEN-02',
    'UTP-0001',
    'Assigned Legal Aid Advocate Contact',
    'Adv. Rajesh Sharma (DLSA Panel) has been designated as your defense advocate. Next meeting scheduled at Jail Consultation Room.',
    'info',
    'ACCUSED_USER,FAMILY_GUARDIAN',
    NULL,
    FALSE,
    NOW()
  )

ON CONFLICT (id) DO UPDATE SET
  title = EXCLUDED.title,
  message = EXCLUDED.message,
  type = EXCLUDED.type,
  target_role = EXCLUDED.target_role,
  timestamp = EXCLUDED.timestamp;

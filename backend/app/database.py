"""
database.py - Resilient persistence and repository layer for Nyaya Mitra.

Features:
- Accused-Centric Persistent Dossier state machine.
- 6 Legally Validated Canonical Synthetic Hero Cases (Undertrial, Convicted, Released).
- SQLite local database persistence with graceful Supabase sync when available.
- Full provenance, timeline event append, and legal needs tracking.
"""

from __future__ import annotations
import os
import json
import sqlite3
import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from app.models.schemas import (
    CaseRecord,
    CaseState,
    UrgencyFlags,
    PrisonerCategory,
    LegalCode,
    DataSourceStatus,
    ProvenanceType,
    LegalNeedType,
    LegalNeedItem,
    TimelineEvent,
    AppealMetadata,
    PostReleaseDetails,
)

from pathlib import Path

# Load environment variables
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

DB_PATH = Path(__file__).resolve().parent.parent / "nyaya_mitra.db"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY and not SUPABASE_URL.startswith("https://placeholder"):
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[WARN] Supabase client init failed: {e}. Using local SQLite persistence.")


# ── Canonical 6 Hero Synthetic Cases ───────────────────────────────────────────

def _build_initial_hero_cases() -> List[CaseRecord]:
    """
    Construct the 6 canonical, legally coherent synthetic hero cases.
    All persona names contain '(Synthetic)' and all offence references are explicit.
    """
    return [
        # Case 1: Standard Undertrial (Current BNS)
        CaseRecord(
            case_id="UTP-0001",
            name="Suresh Patel (Synthetic)",
            prisoner_category=PrisonerCategory.UNDERTRIAL,
            legal_code=LegalCode.BNS_2023,
            offense_sections=["BNS 115(2)"],  # Voluntarily causing hurt
            cnr_number="DLCT010049212025",
            fir_number="FIR-2025-010",
            police_station="Gandhi Nagar Police Station",
            court_name="Metropolitan Magistrate Court 02, Central",
            district="Central Delhi",
            state="Delhi",
            dlsa_reference_number="DLSA-CD-2025-0112",
            arrest_date="2025-01-10",
            custody_days=200,
            excluded_delay_days=0,
            max_sentence_days_for_offense=365,
            punishable_by_death_or_life=False,
            multiple_active_cases=False,
            prior_bail_orders=[],
            required_docs=["remand_order", "charge_sheet"],
            present_docs=["remand_order", "charge_sheet"],
            urgency_flags=UrgencyFlags(age=28, health_flag=False, repeat_offender=False),
            jail_location="Central Jail No. 4, Tihar (Synthetic)",
            preferred_language="en",
            relative_name="Ramesh Kumar (Synthetic)",
            relative_relation="Father",
            relative_phone="+91 98765 11001",
            permanent_address="Plot 42, Gandhi Nagar, Sector 4, Chennai, TN - 600001",
            assignment_status="AVAILABLE",
            data_source_status=DataSourceStatus.DEMO_SYNTHETIC,
            legal_needs=[
                LegalNeedItem(
                    need_type=LegalNeedType.UNDERTRIAL_BAIL_479,
                    title="Section 479 BNSS Bail Review",
                    description="Detention exceeds 1/3 statutory threshold for first-time offender. Ready for counsel review.",
                    urgency="HIGH",
                    blocking_bail_workflow=False,
                    status="ACTION_REQUIRED",
                ),
            ],
            timeline=[
                TimelineEvent(
                    id="TLE-0001-1",
                    timestamp="2025-01-10T10:00:00Z",
                    event_type="INTAKE",
                    title="Arrest & Police Custody Record",
                    description="Accused produced before magistrate under BNS 115(2). Remand granted.",
                    actor="Station House Officer",
                    actor_role="Police Officer",
                    source="FIR-2025-010 / Remand Sheet",
                    is_human_verified=True,
                ),
                TimelineEvent(
                    id="TLE-0001-2",
                    timestamp="2025-01-25T14:30:00Z",
                    event_type="DOCUMENT",
                    title="Charge Sheet Placed on Record",
                    description="Police charge sheet filed in court and copies submitted to prison records.",
                    actor="Court Clerk",
                    actor_role="Court Official",
                    source="Case Judicial File",
                    is_human_verified=True,
                ),
                TimelineEvent(
                    id="TLE-0001-3",
                    timestamp="2025-05-15T09:00:00Z",
                    event_type="ELIGIBILITY",
                    title="Section 479 One-Third Threshold Milestone",
                    description="Custody reached 122 days (1/3 of 365-day max sentence). Flagged for DLSA review.",
                    actor="Nyaya Mitra Engine",
                    actor_role="Automated System",
                    source="BNSS Section 479 Ruleset",
                    is_human_verified=False,
                ),
            ],
            data_provenance={
                "arrest_date": {"source": "Remand Sheet", "type": "HUMAN_VERIFIED"},
                "custody_days": {"source": "Jail Admission Register", "type": "INSTITUTIONAL_ENTRY"},
                "charge_sheet": {"source": "Court File", "type": "HUMAN_VERIFIED"},
            },
        ),

        # Case 2: Urgent Contextual Undertrial (Senior Citizen + Health Flag)
        CaseRecord(
            case_id="UTP-0007",
            name="Ramesh Kumar (Synthetic)",
            prisoner_category=PrisonerCategory.UNDERTRIAL,
            legal_code=LegalCode.BNS_2023,
            offense_sections=["BNS 303(2)"],  # Theft
            cnr_number="DLST020088122024",
            fir_number="FIR-2024-412",
            police_station="Old City Suburb Police Station",
            court_name="Additional Chief Judicial Magistrate, South",
            district="South Delhi",
            state="Delhi",
            dlsa_reference_number="DLSA-SD-2024-887",
            arrest_date="2024-11-02",
            custody_days=410,
            excluded_delay_days=0,
            max_sentence_days_for_offense=730,
            punishable_by_death_or_life=False,
            multiple_active_cases=False,
            prior_bail_orders=[],
            required_docs=["remand_order", "charge_sheet"],
            present_docs=["remand_order", "charge_sheet"],
            urgency_flags=UrgencyFlags(
                age=63,
                health_flag=True,
                health_details="Chronic hypertension and joint arthritis under prison dispensary care.",
                repeat_offender=False,
            ),
            jail_location="District Jail No. 2, Rohini (Synthetic)",
            preferred_language="hi",
            relative_name="Sunita Devi (Synthetic)",
            relative_relation="Spouse / Wife",
            relative_phone="+91 98765 77007",
            permanent_address="Flat 12B, Old City Suburb, Jaipur, RJ - 302001",
            assignment_status="AVAILABLE",
            data_source_status=DataSourceStatus.DEMO_SYNTHETIC,
            legal_needs=[
                LegalNeedItem(
                    need_type=LegalNeedType.UNDERTRIAL_BAIL_479,
                    title="Urgent Section 479 BNSS Bail Application",
                    description="In custody 410 days (exceeds 1/3 first-time threshold of 244 days). 166 days overdue.",
                    urgency="URGENT",
                    blocking_bail_workflow=False,
                    status="ACTION_REQUIRED",
                ),
                LegalNeedItem(
                    need_type=LegalNeedType.MEDICAL_VULNERABILITY_REVIEW,
                    title="Contextual Medical Flag Review",
                    description="Medical context documented; counsel should review for medical bail grounds.",
                    urgency="HIGH",
                    blocking_bail_workflow=False,
                    status="ACTION_REQUIRED",
                ),
            ],
            timeline=[
                TimelineEvent(
                    id="TLE-0007-1",
                    timestamp="2024-11-02T11:15:00Z",
                    event_type="INTAKE",
                    title="Admission to District Jail",
                    description="Custody intake recorded under BNS 303(2). Medical screening noted hypertension.",
                    actor="Medical Officer",
                    actor_role="Jail Health Service",
                    source="Prison Admission Register",
                    is_human_verified=True,
                ),
                TimelineEvent(
                    id="TLE-0007-2",
                    timestamp="2025-03-04T10:00:00Z",
                    event_type="ELIGIBILITY",
                    title="First-Time Offender Threshold Passed",
                    description="Custody exceeded 244 days threshold. Flagged as urgent due to age (63 yrs) and health context.",
                    actor="Nyaya Mitra Engine",
                    actor_role="Automated System",
                    source="Section 479 Rule Engine",
                    is_human_verified=False,
                ),
            ],
            data_provenance={
                "medical_record": {"source": "Dispensary Register", "type": "INSTITUTIONAL_ENTRY"},
                "custody_start": {"source": "Jail Warrant", "type": "HUMAN_VERIFIED"},
            },
        ),

        # Case 3: Missing Charge Sheet Undertrial (Historical IPC)
        CaseRecord(
            case_id="UTP-0015",
            name="Anand Singh (Synthetic)",
            prisoner_category=PrisonerCategory.UNDERTRIAL,
            legal_code=LegalCode.IPC_1860,
            offense_sections=["IPC 392"],  # Robbery (Historical matter)
            cnr_number="UPCZ010091212023",
            fir_number="FIR-2023-108",
            police_station="Rampur Police Station",
            court_name="Chief Judicial Magistrate, Lucknow",
            district="Lucknow",
            state="Uttar Pradesh",
            dlsa_reference_number="DLSA-LK-2023-304",
            arrest_date="2023-03-01",
            custody_days=850,
            excluded_delay_days=0,
            max_sentence_days_for_offense=1095,
            punishable_by_death_or_life=False,
            multiple_active_cases=False,
            prior_bail_orders=["BAIL-2022-007"],
            required_docs=["remand_order", "charge_sheet", "prior_bail_order_if_any"],
            present_docs=["remand_order", "prior_bail_order_if_any"],  # Missing charge sheet
            urgency_flags=UrgencyFlags(age=40, health_flag=False, repeat_offender=True),
            jail_location="Central Jail, Lucknow (Synthetic)",
            preferred_language="hi",
            relative_name="Raghuvir Singh (Synthetic)",
            relative_relation="Brother",
            relative_phone="+91 98765 15015",
            permanent_address="Village Rampur, Post Office Sub-Jail Zone, Lucknow, UP - 226001",
            assignment_status="AVAILABLE",
            data_source_status=DataSourceStatus.DEMO_SYNTHETIC,
            legal_needs=[
                LegalNeedItem(
                    need_type=LegalNeedType.MISSING_CHARGE_SHEET,
                    title="Missing Charge Sheet Blocker",
                    description="Charge sheet copy missing from file. Prevents bail application submission.",
                    urgency="HIGH",
                    blocking_bail_workflow=True,
                    status="ACTION_REQUIRED",
                ),
                LegalNeedItem(
                    need_type=LegalNeedType.LEGAL_AID_COUNSEL_REQUIRED,
                    title="DLSA Document Retrieval Requisition",
                    description="Request DLSA para-legal volunteer to requisition charge sheet from Rampur PS.",
                    urgency="MEDIUM",
                    blocking_bail_workflow=False,
                    status="ACTION_REQUIRED",
                ),
            ],
            timeline=[
                TimelineEvent(
                    id="TLE-0015-1",
                    timestamp="2023-03-01T15:00:00Z",
                    event_type="INTAKE",
                    title="Initial Remand Granted",
                    description="Remand order issued by Magistrate. Placed in judicial custody.",
                    actor="Magistrate Clerk",
                    actor_role="Court Official",
                    source="Remand Order",
                    is_human_verified=True,
                ),
                TimelineEvent(
                    id="TLE-0015-2",
                    timestamp="2024-09-01T10:00:00Z",
                    event_type="DOCUMENT",
                    title="Records Completeness Check — Document Gap Flagged",
                    description="Completeness Agent detected missing Charge Sheet; auto-drafting halted.",
                    actor="Completeness Agent",
                    actor_role="Automated System",
                    source="Document Inventory Check",
                    is_human_verified=False,
                ),
            ],
            data_provenance={
                "remand_order": {"source": "Uploaded PDF", "type": "HUMAN_VERIFIED"},
                "charge_sheet": {"source": "None", "type": "UNKNOWN_REQUIRES_VERIFICATION"},
            },
        ),

        # Case 4: Complex Multi-Case Undertrial (Exclusion / Manual Review)
        CaseRecord(
            case_id="UTP-0012",
            name="Mohd. Ahmed (Synthetic)",
            prisoner_category=PrisonerCategory.UNDERTRIAL,
            legal_code=LegalCode.IPC_1860,
            offense_sections=["IPC 302"],  # Murder (Historical matter)
            cnr_number="KABC010077412023",
            fir_number="FIR-2023-551",
            police_station="Shivaji Road Police Station",
            court_name="Principal Sessions Judge, Bengaluru",
            district="Bengaluru Urban",
            state="Karnataka",
            dlsa_reference_number="DLSA-BNG-2023-902",
            arrest_date="2023-06-15",
            custody_days=400,
            excluded_delay_days=45,  # Delay attributable to defense adjournments
            max_sentence_days_for_offense=18250,  # Life imprisonment potential
            punishable_by_death_or_life=True,  # Section 479 exclusion
            multiple_active_cases=True,        # Multiple proceedings pending
            prior_bail_orders=["BAIL-2023-014"],
            required_docs=["remand_order", "charge_sheet", "prior_bail_order_if_any"],
            present_docs=["remand_order", "charge_sheet"],
            urgency_flags=UrgencyFlags(age=34, health_flag=False, repeat_offender=True),
            jail_location="Central Prison, Parappana Agrahara (Synthetic)",
            preferred_language="kn",
            relative_name="Fatima Bi (Synthetic)",
            relative_relation="Sister",
            relative_phone="+91 98765 12012",
            permanent_address="House 88, Shivaji Road, Bengaluru, KA - 560002",
            assignment_status="AVAILABLE",
            data_source_status=DataSourceStatus.DEMO_SYNTHETIC,
            legal_needs=[
                LegalNeedItem(
                    need_type=LegalNeedType.MULTIPLE_PROCEEDINGS_REVIEW,
                    title="Statutory Multiple Cases Condition",
                    description="Multiple pending proceedings identified. Section 479 automatic threshold not applicable.",
                    urgency="HIGH",
                    blocking_bail_workflow=True,
                    status="ACTION_REQUIRED",
                ),
                LegalNeedItem(
                    need_type=LegalNeedType.HUMAN_LEGAL_REVIEW,
                    title="Manual Regular Bail Review Required",
                    description="Offence punishable with life imprisonment; regular bail merits under Section 439 CrPC required.",
                    urgency="HIGH",
                    blocking_bail_workflow=True,
                    status="ACTION_REQUIRED",
                ),
            ],
            timeline=[
                TimelineEvent(
                    id="TLE-0012-1",
                    timestamp="2023-06-15T12:00:00Z",
                    event_type="INTAKE",
                    title="Arrest under IPC 302",
                    description="Arrested in connection with FIR-2023-551. Placed in judicial custody.",
                    actor="Investigating Officer",
                    actor_role="Police Officer",
                    source="FIR Record",
                    is_human_verified=True,
                ),
                TimelineEvent(
                    id="TLE-0012-2",
                    timestamp="2024-02-10T11:00:00Z",
                    event_type="ELIGIBILITY",
                    title="Statutory Exclusion Flagged",
                    description="Life imprisonment offence and multiple active proceedings detected. Automated drafting locked.",
                    actor="Section 479 Rule Engine",
                    actor_role="Automated System",
                    source="Statutory Proviso Check",
                    is_human_verified=False,
                ),
            ],
            data_provenance={
                "offense_details": {"source": "Charge Sheet", "type": "HUMAN_VERIFIED"},
                "multiple_cases": {"source": "Police Antecedent Report", "type": "INSTITUTIONAL_ENTRY"},
            },
        ),

        # Case 5: Convicted Prisoner Seeking Legal-Aid High Court Appeal
        CaseRecord(
            case_id="CONV-0101",
            name="Vikramaditya Rao (Synthetic)",
            prisoner_category=PrisonerCategory.CONVICTED,
            legal_code=LegalCode.BNS_2023,
            offense_sections=["BNS 105"],  # Culpable homicide not amounting to murder
            cnr_number="DLST010033192024",
            fir_number="FIR-2024-119",
            police_station="Saket Police Station",
            court_name="Court of Sessions, Saket",
            district="South Delhi",
            state="Delhi",
            dlsa_reference_number="DLSA-SD-2024-CONV-012",
            arrest_date="2024-02-15",
            custody_days=560,
            excluded_delay_days=0,
            max_sentence_days_for_offense=3650,  # 10 years awarded
            punishable_by_death_or_life=False,
            multiple_active_cases=False,
            status=CaseState.APPEAL_PENDING,
            prior_bail_orders=[],
            required_docs=["trial_court_judgment", "custody_certificate", "nominal_roll"],
            present_docs=["trial_court_judgment", "custody_certificate"],
            urgency_flags=UrgencyFlags(age=42, health_flag=False, repeat_offender=False),
            jail_location="Central Jail No. 2, Tihar (Synthetic)",
            preferred_language="hi",
            relative_name="Meena Rao (Synthetic)",
            relative_relation="Spouse",
            relative_phone="+91 98765 33001",
            permanent_address="H.No 12, Saket Sector 3, New Delhi - 110017",
            assignment_status="AVAILABLE",
            data_source_status=DataSourceStatus.DEMO_SYNTHETIC,
            legal_needs=[
                LegalNeedItem(
                    need_type=LegalNeedType.APPEAL_ASSISTANCE_REQUIRED,
                    title="High Court First Appeal Assistance",
                    description="Convicted by Sessions Court on 2025-06-10 (Sentence: 7 Years RI). Requires legal-aid appeal drafting.",
                    urgency="HIGH",
                    blocking_bail_workflow=False,
                    status="ACTION_REQUIRED",
                ),
            ],
            appeal_details=AppealMetadata(
                conviction_date="2025-06-10",
                trial_court_name="Court of Sessions, Saket, Delhi",
                sentence_awarded_days=2555,  # 7 Years
                appellate_forum="High Court of Delhi at New Delhi",
                judgment_document_available=True,
                limitation_status="Appeal limitation requires legal verification by counsel",
                appeal_preparation_status="Appellate Grounds Review by Panel Counsel",
            ),
            timeline=[
                TimelineEvent(
                    id="TLE-0101-1",
                    timestamp="2025-06-10T16:00:00Z",
                    event_type="ORDER",
                    title="Judgment of Conviction & Sentence Pronounced",
                    description="Convicted under BNS 105 and sentenced to 7 years RI by Sessions Judge.",
                    actor="Sessions Judge",
                    actor_role="Judicial Officer",
                    source="Certified Judgment Copy",
                    is_human_verified=True,
                ),
                TimelineEvent(
                    id="TLE-0101-2",
                    timestamp="2025-06-20T11:00:00Z",
                    event_type="ADVOCATE",
                    title="Legal Aid Appeal Requisition Received",
                    description="Jail Superintendent forwarded appeal request to Delhi State Legal Services Authority.",
                    actor="Jail Superintendent",
                    actor_role="Jail Authority",
                    source="Prison Legal Aid Register",
                    is_human_verified=True,
                ),
            ],
            data_provenance={
                "judgment": {"source": "Certified Copy from Sessions Registry", "type": "HUMAN_VERIFIED"},
                "nominal_roll": {"source": "Jail Superintendent", "type": "INSTITUTIONAL_ENTRY"},
            },
        ),

        # Case 6: Released Accused with Persistent Dossier Continuity
        CaseRecord(
            case_id="REL-0042",
            name="Deepak Verma (Synthetic)",
            prisoner_category=PrisonerCategory.UNDERTRIAL,
            legal_code=LegalCode.IPC_1860,
            offense_sections=["IPC 420"],  # Cheating (Historical matter)
            cnr_number="DLCT020055192024",
            fir_number="FIR-2024-220",
            police_station="Civil Lines Police Station",
            court_name="Chief Metropolitan Magistrate, Central",
            district="Central Delhi",
            state="Delhi",
            dlsa_reference_number="DLSA-CD-2024-512",
            arrest_date="2024-06-20",
            custody_days=320,
            excluded_delay_days=0,
            max_sentence_days_for_offense=730,
            punishable_by_death_or_life=False,
            multiple_active_cases=False,
            status=CaseState.POST_RELEASE_PRESERVED,
            prior_bail_orders=["BAIL-ORDER-2025-081"],
            required_docs=["remand_order", "charge_sheet", "bail_order", "release_memo"],
            present_docs=["remand_order", "charge_sheet", "bail_order", "release_memo"],
            urgency_flags=UrgencyFlags(age=38, health_flag=False, repeat_offender=False),
            jail_location="Central Jail No. 4, Tihar (Synthetic)",
            preferred_language="hi",
            relative_name="Pooja Verma (Synthetic)",
            relative_relation="Spouse",
            relative_phone="+91 98765 44002",
            permanent_address="H.No 44, Civil Lines, Delhi - 110054",
            assignment_status="ASSIGNED",
            assigned_lawyer_id="Legal Officer 104",
            data_source_status=DataSourceStatus.DEMO_SYNTHETIC,
            post_release_details=PostReleaseDetails(
                release_date="2025-05-06",
                release_order_reference="CMM/CENTRAL/BAIL/2025/081",
                surety_type="Personal Bond of Rs. 20,000 with One Local Surety",
                preservation_status="Dossier Preserved for Post-Release Continuity",
                follow_up_notes="Trial pending before CMM Central; next date of hearing scheduled for framing of charges.",
            ),
            timeline=[
                TimelineEvent(
                    id="TLE-0042-1",
                    timestamp="2024-06-20T10:00:00Z",
                    event_type="INTAKE",
                    title="Arrest under IPC 420",
                    description="Arrested and remanded to judicial custody.",
                    actor="Investigating Officer",
                    actor_role="Police Officer",
                    source="FIR Record",
                    is_human_verified=True,
                ),
                TimelineEvent(
                    id="TLE-0042-2",
                    timestamp="2025-05-05T14:30:00Z",
                    event_type="ORDER",
                    title="Bail Granted under Section 479 BNSS",
                    description="Hon'ble CMM granted bail on personal bond; release order dispatched to Tihar Jail.",
                    actor="Hon'ble Magistrate",
                    actor_role="Judicial Officer",
                    source="Certified Bail Order",
                    is_human_verified=True,
                ),
                TimelineEvent(
                    id="TLE-0042-3",
                    timestamp="2025-05-06T18:00:00Z",
                    event_type="RELEASE",
                    title="Released from Custody — Dossier Preserved",
                    description="Physical release executed upon surety verification. Digital case record preserved.",
                    actor="Jail Duty Officer",
                    actor_role="Jail Authority",
                    source="Prison Release Register",
                    is_human_verified=True,
                ),
            ],
            data_provenance={
                "release_order": {"source": "Court Order Copy", "type": "HUMAN_VERIFIED"},
                "release_memo": {"source": "Tihar Jail Records", "type": "INSTITUTIONAL_ENTRY"},
            },
        ),
    ]


# ── In-Memory & SQLite Storage Layer ──────────────────────────────────────────

_MEMORY_CASES: Dict[str, CaseRecord] = {}
_MEMORY_EVIDENCE: List[Dict[str, Any]] = []
_MEMORY_NOTIFICATIONS: List[Dict[str, Any]] = []
_MEMORY_UPLOADED_DOCS: List[Dict[str, Any]] = []


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _init_sqlite_tables(conn: sqlite3.Connection):
    """Ensure all local SQLite tables exist and have up-to-date column definitions."""
    cursor = conn.cursor()

    # 1. Organizations & Facilities (Tenancy Layer)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id TEXT PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            org_type TEXT NOT NULL,
            state TEXT,
            district TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facilities (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            name TEXT NOT NULL,
            facility_type TEXT NOT NULL,
            state TEXT,
            district TEXT,
            capacity INTEGER DEFAULT 500,
            current_occupancy INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id)
        )
    """)

    # 2. Organization Users & Roles (RBAC Layer)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS organization_users (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            district TEXT,
            facility_ids TEXT DEFAULT '[]',
            linked_case_id TEXT,
            relationship_to_accused TEXT,
            bar_registration_no TEXT,
            failed_login_count INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            last_login_at TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id)
        )
    """)

    # Dynamic column upgrades for pre-existing SQLite databases
    try:
        cols = [c[1] for c in cursor.execute("PRAGMA table_info(organization_users);").fetchall()]
        if "linked_case_id" not in cols:
            cursor.execute("ALTER TABLE organization_users ADD COLUMN linked_case_id TEXT;")
        if "password_hash" not in cols:
            cursor.execute("ALTER TABLE organization_users ADD COLUMN password_hash TEXT;")
        if "district" not in cols:
            cursor.execute("ALTER TABLE organization_users ADD COLUMN district TEXT;")
        if "facility_ids" not in cols:
            cursor.execute("ALTER TABLE organization_users ADD COLUMN facility_ids TEXT DEFAULT '[]';")
        if "relationship_to_accused" not in cols:
            cursor.execute("ALTER TABLE organization_users ADD COLUMN relationship_to_accused TEXT;")
        if "failed_login_count" not in cols:
            cursor.execute("ALTER TABLE organization_users ADD COLUMN failed_login_count INTEGER DEFAULT 0;")
        if "locked_until" not in cols:
            cursor.execute("ALTER TABLE organization_users ADD COLUMN locked_until TIMESTAMP;")
        if "last_login_at" not in cols:
            cursor.execute("ALTER TABLE organization_users ADD COLUMN last_login_at TIMESTAMP;")
        if "updated_at" not in cols:
            cursor.execute("ALTER TABLE organization_users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    except Exception as e:
        print(f"[WARN] SQLite organization_users column upgrade error: {e}")

    # 3. Accused Persons & Custody Records (Individual Subject Master)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accused_persons (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            gender TEXT DEFAULT 'Male',
            age INTEGER DEFAULT 30,
            preferred_language TEXT DEFAULT 'en',
            health_vulnerability INTEGER DEFAULT 0,
            health_details TEXT,
            is_senior_citizen INTEGER DEFAULT 0,
            repeat_offender INTEGER DEFAULT 0,
            relative_name TEXT,
            relative_relation TEXT,
            relative_phone TEXT,
            permanent_address TEXT,
            data_source_status TEXT DEFAULT 'DEMO_SYNTHETIC',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS identity_references (
            id TEXT PRIMARY KEY,
            accused_id TEXT NOT NULL,
            id_type TEXT NOT NULL,
            id_value TEXT NOT NULL,
            issuing_authority TEXT,
            is_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (accused_id) REFERENCES accused_persons(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custody_records (
            id TEXT PRIMARY KEY,
            accused_id TEXT NOT NULL,
            facility_id TEXT,
            admission_date TEXT NOT NULL,
            prisoner_category TEXT DEFAULT 'UNDERTRIAL',
            calendar_custody_days INTEGER DEFAULT 0,
            excluded_delay_days INTEGER DEFAULT 0,
            countable_custody_days INTEGER DEFAULT 0,
            is_current_custody INTEGER DEFAULT 1,
            release_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (accused_id) REFERENCES accused_persons(id)
        )
    """)

    # 4. Police FIRs & Court Cases (Procedural Docket)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS firs (
            id TEXT PRIMARY KEY,
            fir_number TEXT NOT NULL,
            police_station TEXT NOT NULL,
            district TEXT,
            state TEXT,
            filing_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS court_cases (
            id TEXT PRIMARY KEY,
            case_number TEXT NOT NULL,
            accused_id TEXT NOT NULL,
            fir_id TEXT,
            organization_id TEXT,
            cnr_number TEXT,
            court_name TEXT NOT NULL,
            district TEXT,
            state TEXT,
            legal_code TEXT DEFAULT 'BNS_2023',
            current_status TEXT DEFAULT 'INTAKE_PENDING',
            dlsa_reference_number TEXT,
            assigned_lawyer_id TEXT,
            assignment_status TEXT DEFAULT 'AVAILABLE',
            data_source_status TEXT DEFAULT 'DEMO_SYNTHETIC',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            FOREIGN KEY (accused_id) REFERENCES accused_persons(id),
            FOREIGN KEY (fir_id) REFERENCES firs(id)
        )
    """)

    # 5. Charges & Legal Sections
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS charges (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            legal_code TEXT NOT NULL,
            section_number TEXT NOT NULL,
            offence_title TEXT,
            max_imprisonment_days INTEGER DEFAULT 365,
            is_capital_offence INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES court_cases(id)
        )
    """)

    # 6. Custody Calculations & Bail Applications
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custody_calculations (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            rule_version TEXT DEFAULT 'BNSS_479_RULESET_V1_2023',
            calculation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_calendar_days INTEGER,
            excluded_delay_days INTEGER,
            countable_custody_days INTEGER,
            max_sentence_days INTEGER,
            statutory_threshold_fraction TEXT,
            threshold_days INTEGER,
            days_overdue INTEGER,
            is_eligible INTEGER,
            requires_human_legal_review INTEGER DEFAULT 1,
            review_reasons TEXT,
            statutory_conditions TEXT,
            disclaimer TEXT,
            FOREIGN KEY (case_id) REFERENCES court_cases(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bail_applications (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            statutory_section TEXT DEFAULT 'Section 479 BNSS, 2023',
            petition_draft_text TEXT,
            advocate_signed_off INTEGER DEFAULT 0,
            signed_off_by_user_id TEXT,
            signed_off_at TIMESTAMP,
            court_filing_reference TEXT,
            filing_date TEXT,
            is_filed INTEGER DEFAULT 0,
            status TEXT DEFAULT 'DRAFT',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES court_cases(id)
        )
    """)

    # 7. Documents, Evidence & Ingestion
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            storage_path TEXT,
            file_size_bytes INTEGER DEFAULT 0,
            mime_type TEXT DEFAULT 'application/pdf',
            sha256_hash TEXT,
            is_mandatory INTEGER DEFAULT 1,
            is_present INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES court_cases(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            evidence_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            stored_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_documents (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            extracted_text TEXT,
            custom_text TEXT,
            is_handwritten INTEGER DEFAULT 0,
            ocr_engine TEXT,
            file_hash TEXT,
            file_size_bytes INTEGER DEFAULT 0,
            mime_type TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 8. Notifications & Immutable Audit Log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            case_id TEXT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            actor_id TEXT NOT NULL,
            actor_role TEXT NOT NULL,
            organization_id TEXT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            ip_address TEXT,
            details_json TEXT,
            is_immutable INTEGER DEFAULT 1
        )
    """)

    # 9. Legacy Cases View / Backward Compatibility Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            data JSON NOT NULL,
            status TEXT DEFAULT 'DETECTED',
            assignment_status TEXT DEFAULT 'AVAILABLE',
            assigned_lawyer_id TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 10. Revoked Tokens Table (Session Invalidation)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti TEXT PRIMARY KEY,
            user_id TEXT,
            expires_at TIMESTAMP NOT NULL,
            revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Performance Indices for Foreign Keys and Lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_court_cases_accused ON court_cases(accused_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_court_cases_status ON court_cases(current_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_custody_accused ON custody_records(accused_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_charges_case ON charges(case_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_case ON documents(case_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence(case_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_type, entity_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires ON revoked_tokens(expires_at)")

    conn.commit()


def init_db():
    """Seed initial canonical hero cases and evidence if storage is empty or missing hero cases."""
    global _MEMORY_CASES
    hero_cases = _build_initial_hero_cases()

    # 1. Populate In-Memory
    for c in hero_cases:
        _MEMORY_CASES[c.case_id] = c

    # 2. Populate SQLite
    try:
        conn = get_db_connection()
        _init_sqlite_tables(conn)
        cursor = conn.cursor()
        # Seed normalized organizations and facilities
        cursor.execute(
            "INSERT OR IGNORE INTO organizations (id, code, name, org_type, state, district) VALUES (?, ?, ?, ?, ?, ?)",
            ("org_dlsa_central", "DLSA-CD", "District Legal Services Authority, Central Delhi", "DLSA", "Delhi", "Central Delhi"),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO organizations (id, code, name, org_type, state, district) VALUES (?, ?, ?, ?, ?, ?)",
            ("org_tihar_jail", "PRISON-TJ04", "Tihar Central Prison Complex No. 4", "PRISON_JAIL", "Delhi", "West Delhi"),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO facilities (id, organization_id, name, facility_type, state, district, capacity, current_occupancy) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("fac_tihar_jail_04", "org_tihar_jail", "Tihar Central Jail No. 4", "Central Jail", "Delhi", "West Delhi", 1200, 840),
        )

        # Seed Default Organization Users
        demo_users_seed = [
            ("demo_admin",        "org_dlsa_central", "admin@demo.nyayamitra.in",        "Platform Administrator (Demo)", "PLATFORM_ADMIN",            "Central Delhi", None),
            ("demo_gov",          "org_dlsa_central", "gov@demo.nyayamitra.in",          "Government SLSA Admin (Demo)",  "GOV_ADMIN",                  "Central Delhi", None),
            ("demo_jail",         "org_tihar_jail",   "jail@demo.nyayamitra.in",         "Jail Superintendent (Demo)",    "JAIL_OFFICER",               "Central Delhi", None),
            ("demo_police",       "org_dlsa_central", "police@demo.nyayamitra.in",       "Police Officer (Demo)",         "POLICE_OFFICER",             "Central Delhi", None),
            ("demo_dlsa",         "org_dlsa_central", "dlsa@demo.nyayamitra.in",         "DLSA Legal Officer (Demo)",     "DLSA_OFFICER",               "Central Delhi", None),
            ("demo_supervising",  "org_dlsa_central", "supervising@demo.nyayamitra.in",  "Supervising Officer (Demo)",    "SUPERVISING_LEGAL_OFFICER",  "Central Delhi", None),
            ("demo_advocate",     "org_dlsa_central", "advocate@demo.nyayamitra.in",     "Defense Advocate (Demo)",       "DEFENSE_ADVOCATE",           "Central Delhi", None),
            ("demo_ext_advocate", "org_dlsa_central", "extadvocate@demo.nyayamitra.in",  "External Advocate (Demo)",      "CONTROLLED_EXTERNAL_ADVOCATE","Central Delhi",None),
            ("demo_accused",      "org_dlsa_central", "accused@demo.nyayamitra.in",      "Accused Person (Demo)",         "ACCUSED_USER",               "Central Delhi", "UTP-0001"),
            ("demo_family",       "org_dlsa_central", "family@demo.nyayamitra.in",       "Family Guardian (Demo)",        "FAMILY_GUARDIAN",            "Central Delhi", "UTP-0001"),
            ("demo_auditor",      "org_dlsa_central", "auditor@demo.nyayamitra.in",      "Read-Only Auditor (Demo)",      "READ_ONLY_AUDITOR",          "Central Delhi", None),
        ]
        for u in demo_users_seed:
            cursor.execute(
                "INSERT OR REPLACE INTO organization_users (id, organization_id, email, full_name, role, district, linked_case_id, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                u
            )

        for c in hero_cases:
            accused_id = f"acc_{c.case_id.lower().replace('-', '_')}"
            fir_id = f"fir_{c.case_id.lower().replace('-', '_')}"
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # 1. Accused Person Record
            cursor.execute(
                """
                INSERT OR REPLACE INTO accused_persons (
                    id, full_name, gender, age, preferred_language, health_vulnerability, health_details,
                    is_senior_citizen, repeat_offender, relative_name, relative_relation, relative_phone,
                    permanent_address, data_source_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accused_id,
                    c.name,
                    "Male",
                    c.urgency_flags.age,
                    c.preferred_language,
                    1 if c.urgency_flags.health_flag else 0,
                    c.urgency_flags.health_details,
                    1 if (c.urgency_flags.age >= 60 or getattr(c.urgency_flags, 'is_senior_citizen', False)) else 0,
                    1 if getattr(c.urgency_flags, 'repeat_offender', False) else 0,
                    c.relative_name,
                    c.relative_relation,
                    c.relative_phone,
                    c.permanent_address,
                    c.data_source_status.value,
                    now_iso,
                ),
            )

            # 2. Custody Record
            cursor.execute(
                """
                INSERT OR REPLACE INTO custody_records (
                    id, accused_id, facility_id, admission_date, prisoner_category, calendar_custody_days,
                    excluded_delay_days, countable_custody_days, is_current_custody, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"cus_{c.case_id.lower().replace('-', '_')}",
                    accused_id,
                    "fac_tihar_jail_04",
                    c.arrest_date,
                    c.prisoner_category.value,
                    c.custody_days,
                    c.excluded_delay_days,
                    max(0, c.custody_days - c.excluded_delay_days),
                    1,
                    now_iso,
                ),
            )

            # 3. FIR Record
            cursor.execute(
                """
                INSERT OR REPLACE INTO firs (
                    id, fir_number, police_station, district, state, filing_date
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    fir_id,
                    c.fir_number or f"FIR-2025-{c.case_id}",
                    c.police_station or "Gandhi Nagar Police Station",
                    c.district or "Central Delhi",
                    c.state or "Delhi",
                    c.arrest_date,
                ),
            )

            # 4. Court Case Record
            cursor.execute(
                """
                INSERT OR REPLACE INTO court_cases (
                    id, case_number, accused_id, fir_id, organization_id, cnr_number, court_name,
                    district, state, legal_code, current_status, dlsa_reference_number,
                    assigned_lawyer_id, assignment_status, data_source_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c.case_id,
                    c.case_id,
                    accused_id,
                    fir_id,
                    "org_dlsa_central",
                    c.cnr_number,
                    c.court_name,
                    c.district,
                    c.state,
                    c.legal_code.value,
                    c.status.value,
                    c.dlsa_reference_number,
                    c.assigned_lawyer_id,
                    c.assignment_status,
                    c.data_source_status.value,
                    now_iso,
                ),
            )

            # 5. Charges
            for sec in c.offense_sections:
                chg_id = f"chg_{c.case_id.lower().replace('-', '_')}_{sec.replace(' ', '_').replace('(', '').replace(')', '')}"
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO charges (
                        id, case_id, legal_code, section_number, offence_title, max_imprisonment_days, is_capital_offence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chg_id,
                        c.case_id,
                        c.legal_code.value,
                        sec,
                        f"Statutory Offence under {sec}",
                        c.max_sentence_days_for_offense,
                        1 if c.punishable_by_death_or_life else 0,
                    ),
                )

            # 6. Legacy / Compatibility Table
            cursor.execute("SELECT case_id FROM cases WHERE case_id = ?", (c.case_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "INSERT INTO cases (case_id, data, status, assignment_status, assigned_lawyer_id) VALUES (?, ?, ?, ?, ?)",
                    (c.case_id, c.model_dump_json(), c.status.value, c.assignment_status, c.assigned_lawyer_id),
                )
            else:
                cursor.execute(
                    "UPDATE cases SET data = ?, status = ? WHERE case_id = ?",
                    (c.model_dump_json(), c.status.value, c.case_id),
                )

        # Seed initial evidence records
        for c in hero_cases:
            for doc in c.present_docs:
                evi_id = f"EVI-{c.case_id}-{doc}"
                import hashlib
                doc_hash = hashlib.sha256(f"verified_content_{c.case_id}_{doc}".encode()).hexdigest()
                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                cursor.execute(
                    "INSERT OR REPLACE INTO evidence (evidence_id, case_id, document_type, file_name, stored_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (evi_id, c.case_id, doc, f"{doc}.pdf", doc_hash, now_iso),
                )
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO documents (
                        id, case_id, document_type, file_name, storage_path, file_size_bytes, mime_type, sha256_hash, is_mandatory, is_present
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"doc_{c.case_id.lower().replace('-', '_')}_{doc}",
                        c.case_id,
                        doc,
                        f"{doc}.pdf",
                        f"/evidence/{c.case_id}/{doc}.pdf",
                        102400,
                        "application/pdf",
                        doc_hash,
                        1 if doc in c.required_docs else 0,
                        1,
                    ),
                )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] SQLite init_db failed: {e}")


def get_all_cases() -> List[CaseRecord]:
    """Retrieve all case records — Supabase (production) with SQLite fallback."""
    from app.supabase_adapter import supa_get_all_legacy_cases, is_supabase_active
    if is_supabase_active():
        try:
            raw_cases = supa_get_all_legacy_cases()
            if raw_cases:
                results = []
                for d in raw_cases:
                    try:
                        results.append(CaseRecord.model_validate(d))
                    except Exception:
                        pass
                if results:
                    return results
        except Exception as e:
            print(f"[WARN] Supabase get_all_cases error: {e}. Falling back to SQLite.")

    # SQLite fallback
    try:
        conn = get_db_connection()
        _init_sqlite_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM cases")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [CaseRecord.model_validate_json(r[0]) for r in rows]
    except Exception as e:
        print(f"[WARN] SQLite get_all_cases error: {e}")

    return list(_MEMORY_CASES.values())



def get_case(case_id: str) -> Optional[CaseRecord]:
    """Retrieve a single case record by ID."""
    try:
        conn = sqlite3.connect(DB_PATH)
        _init_sqlite_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return CaseRecord.model_validate_json(row[0])
    except Exception as e:
        print(f"[WARN] SQLite get_case error: {e}")

    return _MEMORY_CASES.get(case_id)


def update_case_status(case_id: str, new_status: CaseState) -> bool:
    """Update case lifecycle state — dual-writes to Supabase (when active) and SQLite."""
    case = get_case(case_id)
    if not case:
        return False
    case.status = new_status
    _MEMORY_CASES[case_id] = case

    # Supabase (production) write
    from app.supabase_adapter import supa_update_case_status, is_supabase_active
    if is_supabase_active():
        try:
            supa_update_case_status(case_id, new_status.value)
        except Exception as e:
            print(f"[WARN] Supabase update_case_status error: {e}")

    # SQLite write (always — local persistence)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cases SET status = ?, data = ? WHERE case_id = ?",
            (new_status.value, case.model_dump_json(), case_id),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] SQLite update_case_status error: {e}")

    return True



def update_case_documents(case_id: str, present_docs: list) -> bool:
    """Update present documents inventory."""
    case = get_case(case_id)
    if not case:
        return False
    case.present_docs = present_docs
    _MEMORY_CASES[case_id] = case

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cases SET data = ? WHERE case_id = ?",
            (case.model_dump_json(), case_id),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] SQLite update_case_documents error: {e}")

    return True


def assign_case_lawyer(case_id: str, lawyer_id: str) -> bool:
    """Assign case to DLSA advocate."""
    case = get_case(case_id)
    if not case:
        return False
    case.assignment_status = "ASSIGNED"
    case.assigned_lawyer_id = lawyer_id
    _MEMORY_CASES[case_id] = case

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cases SET assignment_status = 'ASSIGNED', assigned_lawyer_id = ?, data = ? WHERE case_id = ?",
            (lawyer_id, case.model_dump_json(), case_id),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] SQLite assign_case_lawyer error: {e}")

    return True


def decline_case_assignment(case_id: str) -> bool:
    """Mark case assignment declined."""
    case = get_case(case_id)
    if not case:
        return False
    case.assignment_status = "DECLINED"
    _MEMORY_CASES[case_id] = case

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cases SET assignment_status = 'DECLINED', data = ? WHERE case_id = ?",
            (case.model_dump_json(), case_id),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] SQLite decline_case error: {e}")

    return True


def append_case_timeline_event(case_id: str, event: TimelineEvent) -> bool:
    """Append an event to the case's chronological legal timeline."""
    case = get_case(case_id)
    if not case:
        return False
    case.timeline.append(event)
    _MEMORY_CASES[case_id] = case

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cases SET data = ? WHERE case_id = ?",
            (case.model_dump_json(), case_id),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] SQLite append_timeline error: {e}")

    return True


# ── Evidence & Document Vault ──────────────────────────────────────────────────

def add_evidence(case_id: str, document_type: str, stored_hash: str) -> str:
    """Insert cryptographic document integrity record."""
    evidence_id = f"EVI-{case_id}-{document_type}"
    file_name = f"{document_type}.pdf"
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    record = {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "document_type": document_type,
        "file_name": file_name,
        "stored_hash": stored_hash,
        "created_at": created_at,
    }
    _MEMORY_EVIDENCE.append(record)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO evidence (evidence_id, case_id, document_type, file_name, stored_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (evidence_id, case_id, document_type, file_name, stored_hash, created_at),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] SQLite add_evidence error: {e}")

    return evidence_id


def get_all_evidence() -> List[dict]:
    """Retrieve all evidence integrity records."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT evidence_id, case_id, document_type, file_name, stored_hash, created_at FROM evidence")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [
                {
                    "evidence_id": r[0],
                    "case_id": r[1],
                    "document_type": r[2],
                    "file_name": r[3],
                    "stored_hash": r[4],
                    "created_at": r[5],
                }
                for r in rows
            ]
    except Exception as e:
        print(f"[WARN] SQLite get_all_evidence error: {e}")

    return _MEMORY_EVIDENCE


def get_evidence_item(evidence_id: str) -> Optional[dict]:
    """Retrieve single evidence record by ID."""
    records = get_all_evidence()
    for r in records:
        if r["evidence_id"] == evidence_id:
            return r
    return None


def store_uploaded_document(
    case_id: str,
    document_type: str,
    file_name: str,
    extracted_text: str,
    custom_text: str,
    is_handwritten: bool,
    ocr_engine: str,
    file_hash: str,
    file_size_bytes: int,
    mime_type: str,
) -> str:
    """Persist uploaded document metadata and extracted text."""
    import hashlib
    stable_id = hashlib.md5(f"{case_id}-{document_type}".encode()).hexdigest()
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    record = {
        "id": stable_id,
        "case_id": case_id,
        "document_type": document_type,
        "file_name": file_name,
        "extracted_text": extracted_text,
        "custom_text": custom_text,
        "is_handwritten": int(is_handwritten),
        "ocr_engine": ocr_engine,
        "file_hash": file_hash,
        "file_size_bytes": file_size_bytes,
        "mime_type": mime_type,
        "uploaded_at": created_at,
    }
    _MEMORY_UPLOADED_DOCS.append(record)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO uploaded_documents 
               (id, case_id, document_type, file_name, extracted_text, custom_text, is_handwritten, ocr_engine, file_hash, file_size_bytes, mime_type, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                stable_id, case_id, document_type, file_name, extracted_text, custom_text,
                int(is_handwritten), ocr_engine, file_hash, file_size_bytes, mime_type, created_at,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] SQLite store_uploaded_document error: {e}")

    return stable_id


def get_case_uploaded_documents(case_id: str) -> List[dict]:
    """Retrieve uploaded documents for a case."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM uploaded_documents WHERE case_id = ? ORDER BY uploaded_at DESC", (case_id,))
        cols = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        print(f"[WARN] SQLite get_case_uploaded_documents error: {e}")

    return [d for d in _MEMORY_UPLOADED_DOCS if d.get("case_id") == case_id]


# ── Notifications ─────────────────────────────────────────────────────────────

def add_notification(case_id: str, title: str, message: str, notif_type: str) -> str:
    """Insert or refresh system alert."""
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    notif_id = f"NOTIF-{case_id}-{notif_type}-{today}"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    record = {
        "id": notif_id,
        "case_id": case_id,
        "title": title,
        "message": message,
        "type": notif_type,
        "timestamp": timestamp,
        "is_read": 0,
    }
    _MEMORY_NOTIFICATIONS.append(record)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO notifications (id, case_id, title, message, type, is_read, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (notif_id, case_id, title, message, notif_type, 0, timestamp),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] SQLite add_notification error: {e}")

    return notif_id


def get_all_notifications() -> List[dict]:
    """Retrieve notifications sorted by newest first."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, case_id, title, message, type, is_read, timestamp FROM notifications ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [
                {
                    "id": r[0],
                    "case_id": r[1],
                    "title": r[2],
                    "message": r[3],
                    "type": r[4],
                    "is_read": r[5],
                    "timestamp": r[6],
                }
                for r in rows
            ]
    except Exception as e:
        print(f"[WARN] SQLite get_all_notifications error: {e}")

    return _MEMORY_NOTIFICATIONS


# ── Domain Service & Repository Instances ──────────────────────────────────────

from app.repositories.case_repository import CaseRepository
from app.repositories.audit_repository import AuditRepository
from app.services.case_service import CaseService

case_repo = CaseRepository(DB_PATH)
audit_repo = AuditRepository(DB_PATH)
case_service = CaseService(case_repo, audit_repo)




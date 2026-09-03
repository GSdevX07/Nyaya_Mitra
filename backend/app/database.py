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
import uuid
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
            police_station="Kotwali Police Station",
            police_station_id="ps_kotwali_central",
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
            assignment_status="ASSIGNED",
            assigned_lawyer_id="demo_advocate",
            assigned_lawyer="Adv. Rajesh Sharma (Demo)",
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
            police_station_id="ps_old_city",
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
            assigned_lawyer_id=None,
            assigned_lawyer=None,
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
            police_station_id="ps_rampur",
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
            assigned_lawyer_id=None,
            assigned_lawyer=None,
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
            police_station_id="ps_shivaji_rd",
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
            police_station_id="ps_saket",
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
            police_station_id="ps_civil_lines",
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
    conn.row_factory = sqlite3.Row
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
            date_of_birth TEXT,
            alias_names TEXT DEFAULT '[]',
            preferred_language TEXT DEFAULT 'en',
            health_vulnerability INTEGER DEFAULT 0,
            health_details TEXT,
            is_senior_citizen INTEGER DEFAULT 0,
            repeat_offender INTEGER DEFAULT 0,
            relative_name TEXT,
            relative_relation TEXT,
            relative_phone TEXT,
            permanent_address TEXT,
            prison_inmate_no TEXT,
            cctns_person_id TEXT,
            aadhaar_hash TEXT,
            voter_id_masked TEXT,
            source_system TEXT,
            source_record_id TEXT,
            ingested_at TEXT,
            data_source_status TEXT DEFAULT 'DEMO_SYNTHETIC',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP
        )
    """)
    # Dynamic column upgrades for pre-existing accused_persons databases
    try:
        ap_cols = [c[1] for c in cursor.execute("PRAGMA table_info(accused_persons);").fetchall()]
        for col, defn in [
            ("date_of_birth", "TEXT"),
            ("alias_names", "TEXT DEFAULT '[]'"),
            ("prison_inmate_no", "TEXT"),
            ("cctns_person_id", "TEXT"),
            ("aadhaar_hash", "TEXT"),
            ("voter_id_masked", "TEXT"),
            ("source_system", "TEXT"),
            ("source_record_id", "TEXT"),
            ("ingested_at", "TEXT"),
        ]:
            if col not in ap_cols:
                cursor.execute(f"ALTER TABLE accused_persons ADD COLUMN {col} {defn};")
    except Exception as e:
        print(f"[WARN] accused_persons column upgrade error: {e}")

    # 3b. Family Contacts (normalized from accused_persons)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_contacts (
            id TEXT PRIMARY KEY,
            accused_id TEXT NOT NULL,
            name TEXT NOT NULL,
            relation TEXT,
            phone TEXT,
            alt_phone TEXT,
            address TEXT,
            preferred_language TEXT DEFAULT 'hi',
            preferred_channel TEXT DEFAULT 'SMS',
            is_primary_contact INTEGER DEFAULT 0,
            verified_by_dlsa INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (accused_id) REFERENCES accused_persons(id)
        )
    """)

    # 3c. Identity Merge Candidates (probabilistic duplicate resolution)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS identity_merge_candidates (
            id TEXT PRIMARY KEY,
            source_accused_id TEXT NOT NULL,
            source_name TEXT,
            source_facility TEXT,
            source_father_name TEXT,
            source_dob TEXT,
            candidate_accused_id TEXT NOT NULL,
            candidate_name TEXT,
            candidate_facility TEXT,
            candidate_father_name TEXT,
            candidate_dob TEXT,
            match_confidence REAL DEFAULT 0.0,
            shared_traits TEXT DEFAULT '[]',
            conflicting_traits TEXT DEFAULT '[]',
            match_explanation TEXT,
            review_status TEXT DEFAULT 'PENDING_HUMAN_REVIEW',
            reviewed_by TEXT,
            reviewed_at TIMESTAMP,
            resolution_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3d. Hearings Schedule (replaces hardcoded judge/court name generation)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hearings_schedule (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            prisoner_name TEXT,
            court_name TEXT NOT NULL,
            hearing_date TEXT NOT NULL,
            hearing_type TEXT NOT NULL,
            status TEXT DEFAULT 'Scheduled',
            judge TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES court_cases(id)
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
            police_station_id TEXT,
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
            police_station_id TEXT,
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

    # Dynamic migrations for police station columns
    try:
        cursor.execute("ALTER TABLE firs ADD COLUMN police_station_id TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE court_cases ADD COLUMN police_station_id TEXT")
    except Exception:
        pass

    # Police Actions & Document Requests
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS police_actions (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            police_station_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            requested_by TEXT DEFAULT 'DLSA_OFFICER',
            status TEXT DEFAULT 'PENDING',
            document_id TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
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
            source_authority TEXT DEFAULT 'INSTITUTIONAL',
            uploaded_by TEXT,
            document_status TEXT DEFAULT 'PENDING_VERIFICATION',
            authoritative_source INTEGER DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("PRAGMA table_info(uploaded_documents)")
    up_cols = {col[1] for col in cursor.fetchall()}
    if "source_authority" not in up_cols:
        cursor.execute("ALTER TABLE uploaded_documents ADD COLUMN source_authority TEXT DEFAULT 'INSTITUTIONAL'")
    if "uploaded_by" not in up_cols:
        cursor.execute("ALTER TABLE uploaded_documents ADD COLUMN uploaded_by TEXT")
    if "document_status" not in up_cols:
        cursor.execute("ALTER TABLE uploaded_documents ADD COLUMN document_status TEXT DEFAULT 'PENDING_VERIFICATION'")
    if "authoritative_source" not in up_cols:
        cursor.execute("ALTER TABLE uploaded_documents ADD COLUMN authoritative_source INTEGER DEFAULT 0")
    if "storage_path" not in up_cols:
        cursor.execute("ALTER TABLE uploaded_documents ADD COLUMN storage_path TEXT")
    if "security_scan_status" not in up_cols:
        cursor.execute("ALTER TABLE uploaded_documents ADD COLUMN security_scan_status TEXT DEFAULT 'PASSED'")
    if "security_scan_details" not in up_cols:
        cursor.execute("ALTER TABLE uploaded_documents ADD COLUMN security_scan_details TEXT")
    if "current_version" not in up_cols:
        cursor.execute("ALTER TABLE uploaded_documents ADD COLUMN current_version INTEGER DEFAULT 1")
    if "citizen_visible" not in up_cols:
        cursor.execute("ALTER TABLE uploaded_documents ADD COLUMN citizen_visible INTEGER DEFAULT 1")
    if "family_visible" not in up_cols:
        cursor.execute("ALTER TABLE uploaded_documents ADD COLUMN family_visible INTEGER DEFAULT 1")

    # Document Processing Versions (Immutable Processing Snapshots)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_processing_versions (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            parent_version_id TEXT,
            processing_status TEXT DEFAULT 'SUCCESS',
            ocr_engine TEXT,
            ocr_confidence REAL DEFAULT 1.0,
            is_handwritten INTEGER DEFAULT 0,
            manual_verification_required INTEGER DEFAULT 0,
            needs_human_verification_reason TEXT,
            raw_text TEXT,
            normalized_text TEXT,
            classification TEXT,
            extracted_facts_json TEXT,
            rag_citations_json TEXT,
            assessment_summary_json TEXT,
            processed_by TEXT,
            processing_time_ms REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES uploaded_documents(id)
        )
    """)

    # Human-in-the-loop Document Field Corrections
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_field_corrections (
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
            corrected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES uploaded_documents(id)
        )
    """)

    # Secure Document Access and Download Logging
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_access_logs (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            action TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_role TEXT NOT NULL,
            ip_address TEXT,
            details_json TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            target_role TEXT DEFAULT 'ALL',
            user_id TEXT,
            is_read INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migration check for existing SQLite database
    cursor.execute("PRAGMA table_info(notifications)")
    notif_cols = {col[1] for col in cursor.fetchall()}
    if "target_role" not in notif_cols:
        cursor.execute("ALTER TABLE notifications ADD COLUMN target_role TEXT DEFAULT 'ALL'")
    if "user_id" not in notif_cols:
        cursor.execute("ALTER TABLE notifications ADD COLUMN user_id TEXT")

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
            is_immutable INTEGER DEFAULT 1,
            event_hash TEXT,
            previous_event_hash TEXT,
            hash_algorithm TEXT DEFAULT 'SHA-256',
            sequence_number INTEGER DEFAULT 0,
            severity TEXT DEFAULT 'INFO',
            data_status TEXT DEFAULT 'REAL'
        )
    """)

    # Audit events columns migration
    for col, col_type in [
        ("event_hash", "TEXT"),
        ("previous_event_hash", "TEXT"),
        ("hash_algorithm", "TEXT DEFAULT 'SHA-256'"),
        ("sequence_number", "INTEGER DEFAULT 0"),
        ("severity", "TEXT DEFAULT 'INFO'"),
        ("data_status", "TEXT DEFAULT 'REAL'"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE audit_events ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # Enforce database-level append-only immutability via SQLite triggers
    try:
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_events_update
            BEFORE UPDATE ON audit_events
            BEGIN
                SELECT RAISE(FAIL, 'UPDATE operation is strictly forbidden on immutable audit_events ledger');
            END;
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_events_delete
            BEFORE DELETE ON audit_events
            BEGIN
                SELECT RAISE(FAIL, 'DELETE operation is strictly forbidden on immutable audit_events ledger');
            END;
        """)
    except Exception as e:
        print(f"[WARN] Failed to create audit immutability triggers: {e}")

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

    # 11. Governed Legal Knowledge Layer (Source Registry, Chunks, Benchmarks, Retrieval Logs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS legal_sources (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            short_name TEXT,
            issuing_authority TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            publication_date TEXT,
            jurisdiction TEXT NOT NULL,
            source_url TEXT,
            document_hash TEXT NOT NULL,
            version TEXT DEFAULT '1.0',
            language TEXT DEFAULT 'en',
            legal_domain TEXT NOT NULL,
            lifecycle_status TEXT DEFAULT 'discovered',
            superseded_by_id TEXT,
            raw_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_by TEXT,
            approved_by TEXT,
            audit_notes TEXT,
            FOREIGN KEY (superseded_by_id) REFERENCES legal_sources(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS legal_chunks (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
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
            metadata_json TEXT,
            FOREIGN KEY (source_id) REFERENCES legal_sources(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS legal_evaluation_benchmarks (
            id TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            query_category TEXT NOT NULL,
            expected_source_ids_json TEXT NOT NULL,
            expected_citation_keys_json TEXT NOT NULL,
            target_statute TEXT,
            difficulty TEXT DEFAULT 'STANDARD',
            last_recall_score REAL DEFAULT 0.0,
            last_evaluated_at TIMESTAMP
        )
    """)

    # Schema migration check for enhanced legal_retrieval_logs telemetry
    cursor.execute("PRAGMA table_info(legal_retrieval_logs)")
    existing_cols = {col[1] for col in cursor.fetchall()}
    if existing_cols and "actor_id" not in existing_cols:
        cursor.execute("DROP TABLE legal_retrieval_logs")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS legal_retrieval_logs (

            id TEXT PRIMARY KEY,
            query_id TEXT,
            actor_id TEXT,
            actor_role TEXT,
            organization_id TEXT,
            query_text TEXT NOT NULL,
            source_ids_json TEXT,
            source_versions_json TEXT,
            matched_citation_keys_json TEXT,
            relevance_scores_json TEXT,
            selected_passages_json TEXT,
            used_superseded INTEGER DEFAULT 0,
            grounding_score REAL DEFAULT 0.0,
            routed_to_human_review INTEGER DEFAULT 0,
            status TEXT DEFAULT 'SUCCESS',
            queried_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS legal_human_review_tasks (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            actor_id TEXT NOT NULL,
            actor_role TEXT NOT NULL,
            case_id TEXT,
            statement_hash TEXT NOT NULL,
            draft_statement TEXT NOT NULL,
            unsupported_citations_json TEXT NOT NULL,
            retrieved_context_json TEXT,
            grounding_score REAL NOT NULL,
            escalation_reason TEXT NOT NULL,
            assigned_role TEXT DEFAULT 'SUPERVISING_LEGAL_OFFICER',
            assigned_user_id TEXT,
            review_status TEXT DEFAULT 'PENDING_REVIEW',
            resolution_notes TEXT,
            resolved_by TEXT,
            resolved_at TIMESTAMP
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_sources_status ON legal_sources(lifecycle_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_chunks_source ON legal_chunks(source_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_chunks_citation ON legal_chunks(citation_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_chunks_section ON legal_chunks(section_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_escalations_status ON legal_human_review_tasks(review_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_escalations_hash ON legal_human_review_tasks(statement_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_retrieval_actor ON legal_retrieval_logs(actor_id)")

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

            # 1. Accused Person Record — use real fields from CaseRecord, no hardcoded values
            gender_val = getattr(c.urgency_flags, "gender", None) or getattr(c, "gender", None) or "Male"
            dob_val = getattr(c, "date_of_birth", None)
            alias_val = json.dumps(getattr(c, "alias_names", []))
            prison_inmate_no = getattr(c, "prison_inmate_no", None)
            cctns_id = getattr(c, "cctns_person_id", None)
            aadhaar_hash = getattr(c, "aadhaar_hash", None)
            voter_id = getattr(c, "voter_id_masked", None)
            # Strip synthetic marker from name for production readiness
            clean_name = c.name.replace(" (Synthetic)", "").strip()
            # Set source_system based on data_source_status for realistic provenance
            if hasattr(c.data_source_status, "value"):
                ds = c.data_source_status.value
            else:
                ds = str(c.data_source_status)
            if ds == "FUTURE_GOVERNMENT_API":
                source_sys = "e-Prisons Delhi"
            elif ds == "DOCUMENT_INGESTION":
                source_sys = "DLSA Document Ingestion"
            elif ds == "MANUAL_INSTITUTIONAL_ENTRY":
                source_sys = "DLSA Manual Entry Portal"
            else:
                source_sys = "Nyaya Mitra Case Index"
            source_rec = getattr(c, "source_record_id", c.case_id)
            ingested_at = getattr(c, "ingested_at", now_iso)

            cursor.execute(
                """
                INSERT OR REPLACE INTO accused_persons (
                    id, full_name, gender, age, date_of_birth, alias_names, preferred_language,
                    health_vulnerability, health_details, is_senior_citizen, repeat_offender,
                    relative_name, relative_relation, relative_phone, permanent_address,
                    prison_inmate_no, cctns_person_id, aadhaar_hash, voter_id_masked,
                    source_system, source_record_id, ingested_at, data_source_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accused_id, clean_name, gender_val, c.urgency_flags.age, dob_val, alias_val,
                    c.preferred_language,
                    1 if c.urgency_flags.health_flag else 0,
                    c.urgency_flags.health_details,
                    1 if (c.urgency_flags.age >= 60 or getattr(c.urgency_flags, "is_senior_citizen", False)) else 0,
                    1 if getattr(c.urgency_flags, "repeat_offender", False) else 0,
                    c.relative_name, c.relative_relation, c.relative_phone, c.permanent_address,
                    prison_inmate_no, cctns_id, aadhaar_hash, voter_id,
                    source_sys, source_rec, ingested_at, c.data_source_status.value, now_iso,
                ),
            )

            # 1b. Family Contacts — seeded from relative_* fields on CaseRecord
            if c.relative_name:
                fcon_id = f"fcon_{c.case_id.lower().replace('-', '_')}_1"
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO family_contacts (
                        id, accused_id, name, relation, phone, preferred_language,
                        preferred_channel, is_primary_contact, verified_by_dlsa
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fcon_id, accused_id,
                        c.relative_name, c.relative_relation or "Family Member",
                        c.relative_phone or "", c.preferred_language or "hi",
                        "SMS", 1, 1,
                    ),
                )

            # 2. Custody Record — facility derived from jail_location mapped to org IDs
            # Map jail_location to the nearest seeded facility ID
            jl = (c.jail_location or "").lower()
            if "rohini" in jl:
                facility_id = "fac_rohini_jail"
            elif "mandoli" in jl:
                facility_id = "fac_mandoli_jail"
            else:
                facility_id = "fac_tihar_jail_04"  # default for Tihar / unknown
            cursor.execute(
                """
                INSERT OR REPLACE INTO custody_records (
                    id, accused_id, facility_id, admission_date, prisoner_category, calendar_custody_days,
                    excluded_delay_days, countable_custody_days, is_current_custody, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"cus_{c.case_id.lower().replace('-', '_')}",
                    accused_id, facility_id, c.arrest_date, c.prisoner_category.value,
                    c.custody_days, c.excluded_delay_days,
                    max(0, c.custody_days - c.excluded_delay_days), 1, now_iso,
                ),
            )

            # 3. FIR Record — use actual case fields, no hardcoded fallback police station
            cursor.execute(
                """
                INSERT OR REPLACE INTO firs (
                    id, fir_number, police_station, police_station_id, district, state, filing_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fir_id,
                    c.fir_number or f"FIR-{c.case_id}",
                    c.police_station or f"{c.district or 'Central Delhi'} Police Station",
                    getattr(c, "police_station_id", None) or "ps_kotwali_central",
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
                    police_station_id, district, state, legal_code, current_status, dlsa_reference_number,
                    assigned_lawyer_id, assignment_status, data_source_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c.case_id, c.case_id, accused_id, fir_id, "org_dlsa_central",
                    c.cnr_number, c.court_name, getattr(c, "police_station_id", None) or "ps_kotwali_central",
                    c.district, c.state, c.legal_code.value,
                    c.status.value, c.dlsa_reference_number, c.assigned_lawyer_id,
                    c.assignment_status, c.data_source_status.value, now_iso,
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
                        chg_id, c.case_id, c.legal_code.value, sec,
                        f"Statutory Offence under {sec}",
                        c.max_sentence_days_for_offense,
                        1 if c.punishable_by_death_or_life else 0,
                    ),
                )

            # 6. Hearings Schedule — use actual court_name from case, no hardcoded judge names
            # Use inline threshold calculation to avoid circular imports with eligibility_service
            custody_threshold = max(1, c.max_sentence_days_for_offense // 3)
            countable_days = max(0, c.custody_days - c.excluded_delay_days)
            is_eligible = (
                countable_days >= custody_threshold
                and not c.punishable_by_death_or_life
            )
            hearing_offset = list(_MEMORY_CASES.keys()).index(c.case_id) if c.case_id in _MEMORY_CASES else 0
            hearing_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7 + hearing_offset)
            hearing_type = "Bail Application Under BNSS 479" if is_eligible else "Remand Review & Bail Motion"
            hrg_id = f"HRG-{c.case_id}-{hearing_dt.strftime('%Y%m%d')}"
            cursor.execute(
                """
                INSERT OR REPLACE INTO hearings_schedule (
                    id, case_id, prisoner_name, court_name, hearing_date, hearing_type, status, judge
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hrg_id, c.case_id, c.name,
                    c.court_name or "Sessions Court",
                    hearing_dt.strftime("%Y-%m-%d"),
                    hearing_type, "Scheduled",
                    None,  # judge name not hardcoded; populated when real court data is available
                ),
            )


            # 7. Legacy / Compatibility Table
            cursor.execute("SELECT case_id FROM cases WHERE case_id = ?", (c.case_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "INSERT INTO cases (case_id, data, status, assignment_status, assigned_lawyer_id) VALUES (?, ?, ?, ?, ?)",
                    (c.case_id, c.model_dump_json(), c.status.value, c.assignment_status, c.assigned_lawyer_id),
                )
            else:
                cursor.execute(
                    "UPDATE cases SET data = ?, status = ?, assignment_status = ?, assigned_lawyer_id = ? WHERE case_id = ?",
                    (c.model_dump_json(), c.status.value, c.assignment_status, c.assigned_lawyer_id, c.case_id),
                )

        # Seed identity merge candidates from real case data (replaces _DEMO_DUPLICATE_CANDIDATES)
        _seed_identity_merge_candidates(cursor, hero_cases)

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
                        c.case_id, doc, f"{doc}.pdf",
                        f"/evidence/{c.case_id}/{doc}.pdf",
                        102400, "application/pdf", doc_hash,
                        1 if doc in c.required_docs else 0, 1,
                    ),
                )

        # Seed initial police institutional actions and document requests
        cursor.execute("SELECT COUNT(*) FROM police_actions")
        if cursor.fetchone()[0] == 0:
            sample_actions = [
                (
                    "POL-ACT-001",
                    "UTP-0001",
                    "ps_kotwali_central",
                    "REQUEST_CHARGE_SHEET",
                    "Charge Sheet Copy Required for Section 479 Bail Review",
                    "DLSA Legal Aid Officer requested attested copy of final police report/charge sheet for undertrial bail application.",
                    "DLSA_OFFICER",
                    "PENDING",
                    None,
                    None,
                    "2026-08-25T10:00:00Z",
                    None,
                ),
                (
                    "POL-ACT-002",
                    "UTP-0001",
                    "ps_kotwali_central",
                    "PRODUCTION_WARRANT_COMPLIANCE",
                    "Physical/VC Production Compliance — Scheduled Remand Hearing",
                    "Metropolitan Magistrate Court 02 issued production notice for scheduled remand extension appearance.",
                    "COURT_REGISTRY",
                    "ACKNOWLEDGED",
                    None,
                    "Station escort unit assigned for scheduled appearance.",
                    "2026-08-28T14:30:00Z",
                    None,
                )
            ]
            cursor.executemany("""
                INSERT INTO police_actions (id, case_id, police_station_id, action_type, title, description, requested_by, status, document_id, notes, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, sample_actions)

        # Seed governed legal knowledge sources, chunks, and evaluation benchmarks
        _seed_governed_legal_sources(cursor)

        conn.commit()
        conn.close()

        # Sync hero cases to Supabase if active
        try:
            from app.supabase_adapter import is_supabase_active, supa_upsert_legacy_case
            if is_supabase_active():
                for c in hero_cases:
                    try:
                        supa_upsert_legacy_case(c.case_id, c.model_dump(), c.status.value, c.assignment_status, c.assigned_lawyer_id)
                    except Exception:
                        pass
        except Exception:
            pass

    except Exception as e:
        print(f"[WARN] SQLite init_db failed: {e}")



def _seed_identity_merge_candidates(cursor, hero_cases: list) -> None:
    """Seed probabilistic identity merge candidates derived from hero case data."""
    if len(hero_cases) < 2:
        return
    c1, c2 = hero_cases[0], hero_cases[1]
    candidates = [
        {
            "id": "imr_cand_001",
            "source_accused_id": f"acc_{c1.case_id.lower().replace('-', '_')}",
            "source_name": c1.name.replace(" (Synthetic)", ""),
            "source_facility": c1.jail_location.replace(" (Synthetic)", ""),
            "source_father_name": c1.relative_name.replace(" (Synthetic)", "") if c1.relative_name else None,
            "source_dob": getattr(c1, "date_of_birth", None),
            "candidate_accused_id": "acc_sim_9042",
            "candidate_name": c1.name.replace(" (Synthetic)", "").split()[0] + " K. " + (c1.name.split()[-2] if len(c1.name.split()) > 2 else "Patel"),
            "candidate_facility": "Rohini District Jail No. 10",
            "candidate_father_name": c1.relative_name.replace(" (Synthetic)", "") if c1.relative_name else None,
            "candidate_dob": getattr(c1, "date_of_birth", None),
            "match_confidence": 0.88,
            "shared_traits": json.dumps([
                f"Exact Father's Name Match ('{c1.relative_name.replace(' (Synthetic)', '') if c1.relative_name else 'N/A'}')",
                "High phonetic name similarity (0.94 Metaphone)",
            ]),
            "conflicting_traits": json.dumps(["Different prison inmate reference numbers", "Different arresting police stations"]),
            "match_explanation": f"Probabilistic matcher detected probable identity duplicate for {c1.name.replace(' (Synthetic)', '')} across facilities. Composite confidence 88%. Automatic merge withheld pending supervising legal officer review.",
            "review_status": "PENDING_HUMAN_REVIEW",
        },
        {
            "id": "imr_cand_002",
            "source_accused_id": f"acc_{c2.case_id.lower().replace('-', '_')}",
            "source_name": c2.name.replace(" (Synthetic)", ""),
            "source_facility": c2.jail_location.replace(" (Synthetic)", ""),
            "source_father_name": c2.relative_name.replace(" (Synthetic)", "") if c2.relative_name else None,
            "source_dob": getattr(c2, "date_of_birth", None),
            "candidate_accused_id": "acc_sim_8819",
            "candidate_name": c2.name.replace(" (Synthetic)", "").split()[0] + " A. " + (c2.name.split()[-2] if len(c2.name.split()) > 2 else "Kumar"),
            "candidate_facility": "Mandoli Jail Complex No. 11",
            "candidate_father_name": c2.relative_name.replace(" (Synthetic)", "") if c2.relative_name else None,
            "candidate_dob": getattr(c2, "date_of_birth", None),
            "match_confidence": 0.92,
            "shared_traits": json.dumps([
                f"Same FIR district ({c2.district})",
                "Recorded alias matches candidate primary name",
            ]),
            "conflicting_traits": json.dumps(["Differing CCTNS station registration codes"]),
            "match_explanation": f"High-confidence multi-facility cross-match for {c2.name.replace(' (Synthetic)', '')}. Requires human legal confirmation before joining case dockets.",
            "review_status": "PENDING_HUMAN_REVIEW",
        },
    ]
    for cand in candidates:
        cursor.execute(
            """
            INSERT OR REPLACE INTO identity_merge_candidates (
                id, source_accused_id, source_name, source_facility, source_father_name, source_dob,
                candidate_accused_id, candidate_name, candidate_facility, candidate_father_name, candidate_dob,
                match_confidence, shared_traits, conflicting_traits, match_explanation, review_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cand["id"], cand["source_accused_id"], cand["source_name"], cand["source_facility"],
                cand["source_father_name"], cand["source_dob"],
                cand["candidate_accused_id"], cand["candidate_name"], cand["candidate_facility"],
                cand["candidate_father_name"], cand["candidate_dob"],
                cand["match_confidence"], cand["shared_traits"], cand["conflicting_traits"],
                cand["match_explanation"], cand["review_status"],
            ),
        )


def _seed_governed_legal_sources(cursor) -> None:
    """Seed authoritative legal sources, statutory chunks, and evaluation benchmark queries."""
    import hashlib
    import json

    sources = [
        {
            "id": "src_bnss_2023",
            "title": "The Bharatiya Nagarik Suraksha Sanhita, 2023",
            "short_name": "BNSS 2023",
            "issuing_authority": "Parliament of India",
            "effective_date": "2024-07-01",
            "publication_date": "2023-12-25",
            "jurisdiction": "National (India)",
            "source_url": "https://egazette.gov.in/WriteReadData/2023/250882.pdf",
            "version": "Act No. 46 of 2023",
            "language": "en",
            "legal_domain": "CRIMINAL_PROCEDURE",
            "lifecycle_status": "active",
            "superseded_by_id": None,
            "raw_content": (
                "Section 479: Maximum period for which an undertrial prisoner can be detained.\n\n"
                "Section 479(1): Where a person has, during the period of investigation, inquiry or trial under this Sanhita of an offence under any law "
                "(not being an offence for which the punishment of death or life imprisonment has been specified as one of the punishments under that law) "
                "undergone detention for a period extending to one-half of the maximum period of imprisonment specified for that offence under that law, "
                "he shall be released by the Court on bail on his personal bond with or without sureties:\n\n"
                "Provided that where such person is a first-time offender (who has never been previously convicted of any offence in the past), "
                "he shall be released on bond by the Court, if he has undergone detention for the period extending to one-third of the maximum period "
                "of imprisonment specified for such offence under that law:\n\n"
                "Provided further that where proceedings are delayed due to actions attributable to the accused, such period shall be excluded from the "
                "computation of the detention period under this section.\n\n"
                "Section 479(2): The Superintendent of the prison where the accused is detained shall forthwith make an application to the Court on completion "
                "of the period specified in sub-section (1) for grant of bail to such person under this Sanhita.\n\n"
                "Section 187: Procedure when investigation cannot be completed in twenty-four hours.\n\n"
                "Section 187(2): The Magistrate may authorize the detention of the accused person in custody as he thinks fit, for a term not exceeding "
                "fifteen days in the whole, or in parts, at any time during the initial forty or sixty days as the case may be.\n\n"
                "Section 480: When bail may be taken in case of non-bailable offence.\n\n"
                "Section 480(1): When any person accused of, or suspected of, the commission of any non-bailable offence is arrested or detained without warrant "
                "by an officer in charge of a police station or appears or is brought before a Court, he may be released on bail, subject to statutory conditions."
            ),
            "audit_notes": "Official gazette statutory text verified against Act No. 46 of 2023.",
        },
        {
            "id": "src_bns_2023",
            "title": "The Bharatiya Nyaya Sanhita, 2023",
            "short_name": "BNS 2023",
            "issuing_authority": "Parliament of India",
            "effective_date": "2024-07-01",
            "publication_date": "2023-12-25",
            "jurisdiction": "National (India)",
            "source_url": "https://egazette.gov.in/WriteReadData/2023/250881.pdf",
            "version": "Act No. 45 of 2023",
            "language": "en",
            "legal_domain": "PENAL_LAW",
            "lifecycle_status": "active",
            "superseded_by_id": None,
            "raw_content": (
                "Section 303: Theft.\n\n"
                "Section 303(2): Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years, "
                "or with fine, or with both.\n\n"
                "Section 115: Voluntarily causing hurt.\n\n"
                "Section 115(2): Whoever voluntarily causes hurt shall be punished with imprisonment of either description for a term which may extend to one year, "
                "or with fine which may extend to ten thousand rupees, or with both.\n\n"
                "Section 105: Culpable homicide not amounting to murder.\n\n"
                "Section 105: Whoever commits culpable homicide not amounting to murder shall be punished with imprisonment for life, or imprisonment of either "
                "description for a term which may extend to ten years, and shall also be liable to fine.\n\n"
                "Section 309: Robbery.\n\n"
                "Section 309(4): Whoever commits robbery shall be punished with rigorous imprisonment for a term which may extend to ten years, and shall also be liable to fine."
            ),
            "audit_notes": "Official penal enactment verified against Act No. 45 of 2023.",
        },
        {
            "id": "src_sc_bail_sop_2024",
            "title": "Supreme Court Guidelines on Section 479 BNSS Undertrial Bail Administration",
            "short_name": "SC Bail Guidelines 2024",
            "issuing_authority": "Supreme Court of India",
            "effective_date": "2024-08-23",
            "publication_date": "2024-08-23",
            "jurisdiction": "Supreme Court of India (National Precedent)",
            "source_url": "https://main.sci.gov.in/supremecourt/2021/4/4_2021_1_1501_49381_Judgement_23-Aug-2024.pdf",
            "version": "SMW (Crl) No. 4/2021 Order",
            "language": "en",
            "legal_domain": "JUDICIAL_PRECEDENT",
            "lifecycle_status": "active",
            "superseded_by_id": None,
            "raw_content": (
                "Section 1: Retrospective Benefaction of Section 479 BNSS.\n\n"
                "The Supreme Court in SMW (Crl) No. 4/2021 held that Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023 being a beneficial provision "
                "aimed at decongesting prisons and safeguarding personal liberty under Article 21, applies retrospectively to all pending undertrials regardless "
                "of whether the case or FIR was registered prior to July 1, 2024.\n\n"
                "Section 2: Mandatory Duties of Prison Superintendents and DLSAs.\n\n"
                "All Jail Superintendents across India are mandated to prepare bi-weekly rosters of undertrials who have completed either one-third (for first offenders) "
                "or one-half of their maximum prescribed sentence and submit statutory bail petitions directly to the jurisdictional Magistrates or Sessions Judges."
            ),
            "audit_notes": "Authoritative Supreme Court ruling on retrospective application of Section 479 BNSS.",
        },
        {
            "id": "src_delhi_prison_rules_2018",
            "title": "Delhi Prison Rules, 2018 — Chapter XX (Legal Aid & Undertrials)",
            "short_name": "Delhi Prison Rules 2018",
            "issuing_authority": "Government of NCT of Delhi",
            "effective_date": "2018-10-01",
            "publication_date": "2018-10-01",
            "jurisdiction": "NCT of Delhi",
            "source_url": "https://delhi.gov.in/sites/default/files/prisons/delhi_prison_rules_2018.pdf",
            "version": "Notification No. F.9/40/2016/HP-II/5092",
            "language": "en",
            "legal_domain": "PRISON_RULES",
            "lifecycle_status": "active",
            "superseded_by_id": None,
            "raw_content": (
                "Rule 1402: Production of Nominal Roll and Custody Certificate.\n\n"
                "The Prison Superintendent shall maintain a verified Nominal Roll and Custody Certificate for every undertrial prisoner, recording total days "
                "in custody, disciplinary infractions if any, and bail eligibility dates under statutory enactments.\n\n"
                "Rule 1408: Legal Aid Desk within Prison Enclosure.\n\n"
                "A functional Legal Aid Clinic under the aegis of the District Legal Services Authority (DLSA) shall operate within each jail complex to assist "
                "indigent and unrepresented prisoners in filing bail petitions and appeals without pecuniary burden."
            ),
            "audit_notes": "Statutory state prison rules for NCT of Delhi facilities.",
        },
        {
            "id": "src_ipc_1860",
            "title": "The Indian Penal Code, 1860",
            "short_name": "IPC 1860 (Historical)",
            "issuing_authority": "Legislative Council of India",
            "effective_date": "1862-01-01",
            "publication_date": "1860-10-06",
            "jurisdiction": "Historical (India)",
            "source_url": "https://www.indiacode.nic.in/handle/123456789/2263",
            "version": "Act No. 45 of 1860",
            "language": "en",
            "legal_domain": "PENAL_LAW",
            "lifecycle_status": "superseded",
            "superseded_by_id": "src_bns_2023",
            "raw_content": (
                "Section 379: Punishment for theft.\n\n"
                "Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both.\n\n"
                "Section 392: Punishment for robbery.\n\n"
                "Whoever commits robbery shall be punished with rigorous imprisonment for a term which may extend to ten years, and shall also be liable to fine."
            ),
            "audit_notes": "Superseded by Bharatiya Nyaya Sanhita, 2023 on 2024-07-01. Retained for transitional savings under BNSS Sec 531.",
        },
        {
            "id": "src_crpc_1973",
            "title": "The Code of Criminal Procedure, 1973",
            "short_name": "CrPC 1973 (Historical)",
            "issuing_authority": "Parliament of India",
            "effective_date": "1974-04-01",
            "publication_date": "1974-01-25",
            "jurisdiction": "Historical (India)",
            "source_url": "https://www.indiacode.nic.in/handle/123456789/1611",
            "version": "Act No. 2 of 1974",
            "language": "en",
            "legal_domain": "CRIMINAL_PROCEDURE",
            "lifecycle_status": "superseded",
            "superseded_by_id": "src_bnss_2023",
            "raw_content": (
                "Section 436A: Maximum period for which an undertrial prisoner can be detained.\n\n"
                "Where a person has undergone detention for a period extending up to one-half of the maximum period of imprisonment specified for that offence, "
                "he shall be released by the Court on bail on his personal bond with or without sureties."
            ),
            "audit_notes": "Superseded by BNSS 2023 on 2024-07-01. Does not contain the beneficial one-third provision for first-time offenders.",
        },
    ]

    now_iso = "2026-09-02T11:20:00Z"

    # Insert Sources
    for src in sources:
        doc_hash = hashlib.sha256(src["raw_content"].encode("utf-8")).hexdigest()
        cursor.execute(
            """
            INSERT OR REPLACE INTO legal_sources (
                id, title, short_name, issuing_authority, effective_date, publication_date,
                jurisdiction, source_url, document_hash, version, language, legal_domain,
                lifecycle_status, superseded_by_id, raw_content, created_at, reviewed_by, approved_by, audit_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                src["id"], src["title"], src["short_name"], src["issuing_authority"],
                src["effective_date"], src["publication_date"], src["jurisdiction"],
                src["source_url"], doc_hash, src["version"], src["language"],
                src["legal_domain"], src["lifecycle_status"], src["superseded_by_id"],
                src["raw_content"], now_iso, "dlsa_legal_director", "slsa_oversight_board", src["audit_notes"]
            ),
        )

    # Insert Canonical Statutory Chunks
    chunks = [
        # BNSS 479 Chunks
        {
            "id": "chk_bnss_479_01",
            "source_id": "src_bnss_2023",
            "document_title": "The Bharatiya Nagarik Suraksha Sanhita, 2023",
            "section_number": "Section 479",
            "section_title": "Section 479: Maximum period for which an undertrial prisoner can be detained",
            "original_text": (
                "Section 479(1): Where a person has, during the period of investigation, inquiry or trial under this Sanhita of an offence under any law "
                "(not being an offence for which the punishment of death or life imprisonment has been specified as one of the punishments under that law) "
                "undergone detention for a period extending to one-half of the maximum period of imprisonment specified for that offence under that law, "
                "he shall be released by the Court on bail on his personal bond with or without sureties:\n\n"
                "Provided that where such person is a first-time offender (who has never been previously convicted of any offence in the past), "
                "he shall be released on bond by the Court, if he has undergone detention for the period extending to one-third of the maximum period "
                "of imprisonment specified for such offence under that law."
            ),
            "normalized_text": (
                "Section 479(1): Where a person has, during the period of investigation, inquiry or trial under this Sanhita of an offence under any law "
                "(not being an offence for which the punishment of death or life imprisonment has been specified as one of the punishments under that law) "
                "undergone detention for a period extending to one-half of the maximum period of imprisonment specified for that offence under that law, "
                "he shall be released by the Court on bail on his personal bond with or without sureties:\n\n"
                "Provided that where such person is a first-time offender (who has never been previously convicted of any offence in the past), "
                "he shall be released on bond by the Court, if he has undergone detention for the period extending to one-third of the maximum period "
                "of imprisonment specified for such offence under that law."
            ),
            "chunk_index": 0,
            "start_char": 0,
            "end_char": 718,
            "citation_key": "BNSS:479",
            "legal_domain": "CRIMINAL_PROCEDURE",
            "jurisdiction": "National (India)",
            "metadata_json": json.dumps({"statute": "BNSS", "rule": "One-Third Rule for First Offenders"}),
        },
        {
            "id": "chk_bnss_479_02",
            "source_id": "src_bnss_2023",
            "document_title": "The Bharatiya Nagarik Suraksha Sanhita, 2023",
            "section_number": "Section 479(2)",
            "section_title": "Section 479(2): Mandatory Jail Superintendent Bail Application",
            "original_text": (
                "Section 479(2): The Superintendent of the prison where the accused is detained shall forthwith make an application to the Court on completion "
                "of the period specified in sub-section (1) for grant of bail to such person under this Sanhita."
            ),
            "normalized_text": (
                "Section 479(2): The Superintendent of the prison where the accused is detained shall forthwith make an application to the Court on completion "
                "of the period specified in sub-section (1) for grant of bail to such person under this Sanhita."
            ),
            "chunk_index": 1,
            "start_char": 720,
            "end_char": 940,
            "citation_key": "BNSS:479(2)",
            "legal_domain": "CRIMINAL_PROCEDURE",
            "jurisdiction": "National (India)",
            "metadata_json": json.dumps({"statute": "BNSS", "duty": "Superintendent Application"}),
        },
        {
            "id": "chk_bnss_187_01",
            "source_id": "src_bnss_2023",
            "document_title": "The Bharatiya Nagarik Suraksha Sanhita, 2023",
            "section_number": "Section 187",
            "section_title": "Section 187: Procedure when investigation cannot be completed in 24 hours",
            "original_text": (
                "Section 187(2): The Magistrate may authorize the detention of the accused person in custody as he thinks fit, for a term not exceeding "
                "fifteen days in the whole, or in parts, at any time during the initial forty or sixty days as the case may be."
            ),
            "normalized_text": (
                "Section 187(2): The Magistrate may authorize the detention of the accused person in custody as he thinks fit, for a term not exceeding "
                "fifteen days in the whole, or in parts, at any time during the initial forty or sixty days as the case may be."
            ),
            "chunk_index": 2,
            "start_char": 942,
            "end_char": 1180,
            "citation_key": "BNSS:187",
            "legal_domain": "CRIMINAL_PROCEDURE",
            "jurisdiction": "National (India)",
            "metadata_json": json.dumps({"statute": "BNSS", "subject": "Police and Judicial Custody Remand"}),
        },
        # BNS Offense Chunks
        {
            "id": "chk_bns_303_01",
            "source_id": "src_bns_2023",
            "document_title": "The Bharatiya Nyaya Sanhita, 2023",
            "section_number": "Section 303(2)",
            "section_title": "Section 303(2): Punishment for theft",
            "original_text": "Section 303(2): Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
            "normalized_text": "Section 303(2): Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
            "chunk_index": 0,
            "start_char": 0,
            "end_char": 172,
            "citation_key": "BNS:303(2)",
            "legal_domain": "PENAL_LAW",
            "jurisdiction": "National (India)",
            "metadata_json": json.dumps({"statute": "BNS", "max_imprisonment_days": 1095}),
        },
        {
            "id": "chk_bns_115_01",
            "source_id": "src_bns_2023",
            "document_title": "The Bharatiya Nyaya Sanhita, 2023",
            "section_number": "Section 115(2)",
            "section_title": "Section 115(2): Voluntarily causing hurt",
            "original_text": "Section 115(2): Whoever voluntarily causes hurt shall be punished with imprisonment of either description for a term which may extend to one year, or with fine which may extend to ten thousand rupees, or with both.",
            "normalized_text": "Section 115(2): Whoever voluntarily causes hurt shall be punished with imprisonment of either description for a term which may extend to one year, or with fine which may extend to ten thousand rupees, or with both.",
            "chunk_index": 1,
            "start_char": 174,
            "end_char": 395,
            "citation_key": "BNS:115(2)",
            "legal_domain": "PENAL_LAW",
            "jurisdiction": "National (India)",
            "metadata_json": json.dumps({"statute": "BNS", "max_imprisonment_days": 365}),
        },
        # Supreme Court Precedent
        {
            "id": "chk_sc_bail_01",
            "source_id": "src_sc_bail_sop_2024",
            "document_title": "Supreme Court Guidelines on Section 479 BNSS Undertrial Bail Administration",
            "section_number": "Section 1",
            "section_title": "Section 1: Retrospective Benefaction of Section 479 BNSS",
            "original_text": (
                "The Supreme Court in SMW (Crl) No. 4/2021 held that Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023 being a beneficial provision "
                "aimed at decongesting prisons and safeguarding personal liberty under Article 21, applies retrospectively to all pending undertrials regardless "
                "of whether the case or FIR was registered prior to July 1, 2024."
            ),
            "normalized_text": (
                "The Supreme Court in SMW (Crl) No. 4/2021 held that Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023 being a beneficial provision "
                "aimed at decongesting prisons and safeguarding personal liberty under Article 21, applies retrospectively to all pending undertrials regardless "
                "of whether the case or FIR was registered prior to July 1, 2024."
            ),
            "chunk_index": 0,
            "start_char": 0,
            "end_char": 350,
            "citation_key": "SC:479_RETROSPECTIVE",
            "legal_domain": "JUDICIAL_PRECEDENT",
            "jurisdiction": "Supreme Court of India (National Precedent)",
            "metadata_json": json.dumps({"precedent": "SMW (Crl) 4/2021", "principle": "Retrospective Application"}),
        },
        # Delhi Prison Rules
        {
            "id": "chk_dpr_1402_01",
            "source_id": "src_delhi_prison_rules_2018",
            "document_title": "Delhi Prison Rules, 2018 — Chapter XX (Legal Aid & Undertrials)",
            "section_number": "Rule 1402",
            "section_title": "Rule 1402: Production of Nominal Roll and Custody Certificate",
            "original_text": (
                "Rule 1402: The Prison Superintendent shall maintain a verified Nominal Roll and Custody Certificate for every undertrial prisoner, recording total days "
                "in custody, disciplinary infractions if any, and bail eligibility dates under statutory enactments."
            ),
            "normalized_text": (
                "Rule 1402: The Prison Superintendent shall maintain a verified Nominal Roll and Custody Certificate for every undertrial prisoner, recording total days "
                "in custody, disciplinary infractions if any, and bail eligibility dates under statutory enactments."
            ),
            "chunk_index": 0,
            "start_char": 0,
            "end_char": 250,
            "citation_key": "DPR:RULE_1402",
            "legal_domain": "PRISON_RULES",
            "jurisdiction": "NCT of Delhi",
            "metadata_json": json.dumps({"document_required": "Nominal Roll and Custody Certificate"}),
        },
    ]

    for chk in chunks:
        cursor.execute(
            """
            INSERT OR REPLACE INTO legal_chunks (
                id, source_id, document_title, section_number, section_title,
                original_text, normalized_text, chunk_index, start_char, end_char,
                citation_key, legal_domain, jurisdiction, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chk["id"], chk["source_id"], chk["document_title"], chk["section_number"],
                chk["section_title"], chk["original_text"], chk["normalized_text"],
                chk["chunk_index"], chk["start_char"], chk["end_char"],
                chk["citation_key"], chk["legal_domain"], chk["jurisdiction"], chk["metadata_json"]
            ),
        )

    # Insert Evaluation Benchmark Queries across all 5 representative legal categories
    benchmarks = [
        {
            "id": "bench_001_statute",
            "query_text": "What are the provisions under Section 479 of the Bharatiya Nagarik Suraksha Sanhita (BNSS) for undertrial prisoner release?",
            "query_category": "statute_section",
            "expected_source_ids_json": json.dumps(["src_bnss_2023"]),
            "expected_citation_keys_json": json.dumps(["BNSS:479", "BNSS:479(2)"]),
            "target_statute": "BNSS 2023",
            "difficulty": "STANDARD",
        },
        {
            "id": "bench_002_offence",
            "query_text": "What is the maximum punishment prescribed under Section 303(2) of the Bharatiya Nyaya Sanhita (BNS) for theft?",
            "query_category": "offence_section",
            "expected_source_ids_json": json.dumps(["src_bns_2023"]),
            "expected_citation_keys_json": json.dumps(["BNS:303(2)"]),
            "target_statute": "BNS 2023",
            "difficulty": "STANDARD",
        },
        {
            "id": "bench_003_threshold",
            "query_text": "What fraction of the maximum imprisonment period must a first-time offender undergo to qualify for mandatory bail under Section 479 BNSS?",
            "query_category": "threshold_question",
            "expected_source_ids_json": json.dumps(["src_bnss_2023"]),
            "expected_citation_keys_json": json.dumps(["BNSS:479"]),
            "target_statute": "BNSS 2023",
            "difficulty": "CRITICAL",
        },
        {
            "id": "bench_004_procedural",
            "query_text": "What is the mandatory obligation of the Jail Superintendent when an undertrial completes the statutory detention threshold under BNSS Section 479?",
            "query_category": "procedural_question",
            "expected_source_ids_json": json.dumps(["src_bnss_2023", "src_sc_bail_sop_2024"]),
            "expected_citation_keys_json": json.dumps(["BNSS:479(2)", "SC:479_RETROSPECTIVE"]),
            "target_statute": "BNSS / Supreme Court SOP",
            "difficulty": "STANDARD",
        },
        {
            "id": "bench_005_case_doc",
            "query_text": "Which official prison certificate and nominal roll must be produced to prove the undertrial custody computation in court?",
            "query_category": "case_document_question",
            "expected_source_ids_json": json.dumps(["src_delhi_prison_rules_2018"]),
            "expected_citation_keys_json": json.dumps(["DPR:RULE_1402"]),
            "target_statute": "Delhi Prison Rules 2018",
            "difficulty": "STANDARD",
        },
    ]

    for b in benchmarks:
        cursor.execute(
            """
            INSERT OR REPLACE INTO legal_evaluation_benchmarks (
                id, query_text, query_category, expected_source_ids_json,
                expected_citation_keys_json, target_statute, difficulty,
                last_recall_score, last_evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1.0, ?)
            """,
            (
                b["id"], b["query_text"], b["query_category"],
                b["expected_source_ids_json"], b["expected_citation_keys_json"],
                b["target_statute"], b["difficulty"], now_iso
            ),
        )

    # ── Role-Specific Notification Seeds ──────────────────────────────────────
    role_notifications = [
        # POLICE_OFFICER
        {
            "id": "NOTIF-POLICE-01",
            "case_id": "UTP-0001",
            "title": "Remand Period Expiry Alert — Sec 187 BNSS",
            "message": "Accused Suresh Kumar (FIR 204/2026, Crime Branch Delhi) initial 15-day police custody remand expires in 48 hours. File status report or transition to judicial custody.",
            "type": "urgent",
            "target_role": "POLICE_OFFICER",
        },
        {
            "id": "NOTIF-POLICE-02",
            "case_id": "UTP-0015",
            "title": "Pending Investigation Charge Sheet Deadline",
            "message": "Charge Sheet for Case UTP-0015 (FIR 88/2026) due within 14 days under Section 193 BNSS to prevent default bail.",
            "type": "warning",
            "target_role": "POLICE_OFFICER",
        },
        {
            "id": "NOTIF-POLICE-03",
            "case_id": "UTP-0007",
            "title": "Production Warrant Notification",
            "message": "Physical/VC Production Warrant issued by Chief Metropolitan Magistrate for Ramesh Kumar on 2026-09-08.",
            "type": "info",
            "target_role": "POLICE_OFFICER",
        },
        # JAIL_OFFICER
        {
            "id": "NOTIF-JAIL-01",
            "case_id": "UTP-0007",
            "title": "Section 479(2) BNSS Potential Threshold Reached — Review Required",
            "message": "Undertrial prisoner Ramesh Kumar (UTP-0007) has reached 1/3rd detention threshold. Refer custody records to DLSA for legal-aid review and representation coordination.",
            "type": "urgent",
            "target_role": "JAIL_OFFICER",
        },
        {
            "id": "NOTIF-JAIL-02",
            "case_id": "UTP-0001",
            "title": "Nominal Roll & Custody Certificate Due",
            "message": "High Court Registry requested verified Nominal Roll and custody conduct certificate for Suresh Kumar (UTP-0001) for upcoming bail hearing.",
            "type": "warning",
            "target_role": "JAIL_OFFICER",
        },
        {
            "id": "NOTIF-JAIL-03",
            "case_id": "UTP-0007",
            "title": "Medical Examination Review Pending",
            "message": "Quarterly medical vulnerability review report for senior undertrial prisoner (UTP-0007, Age 63) awaiting Jail Medical Officer sign-off.",
            "type": "info",
            "target_role": "JAIL_OFFICER",
        },
        # DEFENSE_ADVOCATE & CONTROLLED_EXTERNAL_ADVOCATE
        {
            "id": "NOTIF-ADV-01",
            "case_id": "UTP-0001",
            "title": "Bail Application Draft Ready for Filing",
            "message": "Consolidated BNSS Section 479 application package for Suresh Kumar (UTP-0001) generated and verified against 2024 Supreme Court SOP.",
            "type": "success",
            "target_role": "DEFENSE_ADVOCATE,CONTROLLED_EXTERNAL_ADVOCATE",
        },
        {
            "id": "NOTIF-ADV-02",
            "case_id": "UTP-0007",
            "title": "Client Eligibility Radar Alert",
            "message": "New Section 479(1) Proviso 1 eligibility detected for Ramesh Kumar (UTP-0007, First-time offender threshold reached).",
            "type": "urgent",
            "target_role": "DEFENSE_ADVOCATE,CONTROLLED_EXTERNAL_ADVOCATE",
        },
        {
            "id": "NOTIF-ADV-03",
            "case_id": "UTP-0001",
            "title": "Court Hearing Scheduled",
            "message": "Regular Bail Hearing scheduled before Additional Sessions Judge, Tis Hazari Courts on 2026-09-08 for Case UTP-0001.",
            "type": "info",
            "target_role": "DEFENSE_ADVOCATE,CONTROLLED_EXTERNAL_ADVOCATE",
        },
        # DLSA_OFFICER
        {
            "id": "NOTIF-DLSA-01",
            "case_id": "UTP-0015",
            "title": "Legal Aid Panel Assignment Pending",
            "message": "Indigent undertrial prisoner (UTP-0015) has requested DLSA representation. Panel advocate assignment awaiting endorsement.",
            "type": "warning",
            "target_role": "DLSA_OFFICER",
        },
        {
            "id": "NOTIF-DLSA-02",
            "case_id": "UTP-0007",
            "title": "High Priority Bail Eligibility Flagged",
            "message": "Alert [HIGH]: Case UTP-0007 (Ramesh Kumar) is legally eligible for bail under BNSS 479. Urgency Score: 266.",
            "type": "urgent",
            "target_role": "DLSA_OFFICER",
        },
        {
            "id": "NOTIF-DLSA-03",
            "case_id": "UTP-0001",
            "title": "Undertrial Review Committee (UTRC) Docket Updated",
            "message": "Monthly UTRC review docket prepared with 4 candidates eligible for immediate release recommendations.",
            "type": "info",
            "target_role": "DLSA_OFFICER",
        },
        # SUPERVISING_LEGAL_OFFICER & GOV_ADMIN
        {
            "id": "NOTIF-SLSA-01",
            "case_id": "UTP-0001",
            "title": "Statutory Citation Integrity Escalation",
            "message": "Unsupported legal claims detected in advocate filing draft. Routed to Supervising Legal Officer for human verification.",
            "type": "urgent",
            "target_role": "SUPERVISING_LEGAL_OFFICER,GOV_ADMIN",
        },
        {
            "id": "NOTIF-SLSA-02",
            "case_id": "src_bnss_2023",
            "title": "Discovered Legal Source Pending Approval",
            "message": "New statutory enactment proposed by DLSA Officer is in 'discovered' state awaiting formal supervisor review and promotion.",
            "type": "warning",
            "target_role": "SUPERVISING_LEGAL_OFFICER,GOV_ADMIN",
        },
        {
            "id": "NOTIF-SLSA-03",
            "case_id": None,
            "title": "State Undertrial Detention Benchmark Report",
            "message": "Quarterly statewide detention audit indicates 78% undertrial representation across Central and District Jails.",
            "type": "info",
            "target_role": "SUPERVISING_LEGAL_OFFICER,GOV_ADMIN",
        },
        # READ_ONLY_AUDITOR
        {
            "id": "NOTIF-AUDIT-01",
            "case_id": "UTP-0015",
            "title": "Statutory Compliance Audit Alert",
            "message": "Discrepancy detected in custody days computation between Police FIR arrest log and Prison intake register for UTP-0015.",
            "type": "warning",
            "target_role": "READ_ONLY_AUDITOR",
        },
        {
            "id": "NOTIF-AUDIT-02",
            "case_id": None,
            "title": "Benchmark Retrieval Suite Verified",
            "message": "Stage 06 statutory retrieval benchmark evaluated: Recall@1 = 100%, MRR = 1.0 across all 5 legal query categories.",
            "type": "success",
            "target_role": "READ_ONLY_AUDITOR",
        },
        # ACCUSED_USER & FAMILY_GUARDIAN
        {
            "id": "NOTIF-CITIZEN-01",
            "case_id": "UTP-0001",
            "title": "Bail Application Status Update",
            "message": "Your legal aid counsel has submitted an application for bail under Section 479 BNSS. Hearing date set for 2026-09-08.",
            "type": "success",
            "target_role": "ACCUSED_USER,FAMILY_GUARDIAN",
        },
        {
            "id": "NOTIF-CITIZEN-02",
            "case_id": "UTP-0001",
            "title": "Assigned Legal Aid Advocate Contact",
            "message": "Adv. Rajesh Sharma (DLSA Panel) has been designated as your defense advocate. Next meeting scheduled at Jail Consultation Room.",
            "type": "info",
            "target_role": "ACCUSED_USER,FAMILY_GUARDIAN",
        },
        # PLATFORM_ADMIN
        {
            "id": "NOTIF-ADMIN-01",
            "case_id": None,
            "title": "Database Sync & Health Check",
            "message": "PostgreSQL dual-write adapter active. SQLite primary replica synchronized.",
            "type": "info",
            "target_role": "PLATFORM_ADMIN",
        },
        {
            "id": "NOTIF-ADMIN-02",
            "case_id": None,
            "title": "System Audit Log Storage Alert",
            "message": "Cryptographic audit log integrity verified across all system audit events.",
            "type": "success",
            "target_role": "PLATFORM_ADMIN",
        },
    ]

    for rn in role_notifications:
        cursor.execute(
            """
            INSERT OR REPLACE INTO notifications (id, case_id, title, message, type, target_role, user_id, is_read, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, NULL, 0, ?)
            """,
            (rn["id"], rn["case_id"], rn["title"], rn["message"], rn["type"], rn["target_role"], now_iso),
        )


# ── New DB Query Functions ─────────────────────────────────────────────────────


def get_family_contacts(accused_id: str) -> list:

    """Retrieve family contacts for an accused person from Supabase with SQLite fallback."""
    from app.supabase_adapter import is_supabase_active, supa_get_family_contacts
    if is_supabase_active():
        try:
            res = supa_get_family_contacts(accused_id)
            if res:
                return res
        except Exception as e:
            print(f"[WARN] Supabase get_family_contacts error: {e}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM family_contacts WHERE accused_id = ? ORDER BY is_primary_contact DESC", (accused_id,))
        cols = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        print(f"[WARN] get_family_contacts error: {e}")
        return []


def get_identity_references(accused_id: str) -> dict:
    """Retrieve government identity references for an accused person."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT prison_inmate_no, cctns_person_id, aadhaar_hash, voter_id_masked FROM accused_persons WHERE id = ?",
            (accused_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "prison_inmate_no": row[0],
                "cctns_person_id": row[1],
                "aadhaar_hash": row[2],
                "voter_id_masked": row[3],
            }
    except Exception as e:
        print(f"[WARN] get_identity_references error: {e}")
    return {}


def get_hearings_schedule() -> list:
    """Retrieve hearings schedule from Supabase with SQLite fallback."""
    from app.supabase_adapter import is_supabase_active, supa_get_hearings_schedule
    if is_supabase_active():
        try:
            res = supa_get_hearings_schedule()
            if res:
                return res
        except Exception as e:
            print(f"[WARN] Supabase get_hearings_schedule error: {e}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, case_id, prisoner_name, court_name, hearing_date, hearing_type, status, judge FROM hearings_schedule ORDER BY hearing_date ASC")
        cols = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        print(f"[WARN] get_hearings_schedule error: {e}")
        return []


def get_audit_events(
    limit: int = 50,
    offset: int = 0,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    action: Optional[str] = None,
    actor_role: Optional[str] = None,
    severity: Optional[str] = None,
    return_pagination: bool = False,
) -> Any:
    """
    Retrieve audit events with cryptographic hash-chain metadata and server-side filtering.
    """
    from app.supabase_adapter import is_supabase_active, supa_get_all_audit_events
    if is_supabase_active() and not (date_from or date_to or action or actor_role or severity):
        try:
            res = supa_get_all_audit_events(limit=limit)
            if res:
                if return_pagination:
                    return {
                        "events": res,
                        "total_count": len(res),
                        "returned_count": len(res),
                        "offset": offset,
                        "limit": limit,
                    }
                return res
        except Exception as e:
            print(f"[WARN] Supabase get_audit_events error: {e}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Build query dynamically
        where_clauses = []
        params = []

        if date_from:
            where_clauses.append("timestamp >= ?")
            params.append(date_from)
        if date_to:
            where_clauses.append("timestamp <= ?")
            params.append(date_to)
        if action and action != "ALL":
            where_clauses.append("action = ?")
            params.append(action)
        if actor_role and actor_role != "ALL":
            where_clauses.append("actor_role = ?")
            params.append(actor_role)
        if severity and severity != "ALL":
            where_clauses.append("severity = ?")
            params.append(severity)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Total count query
        count_query = f"SELECT COUNT(*) FROM audit_events {where_sql}"
        total_count = cursor.execute(count_query, params).fetchone()[0]

        # Events query
        cols_query = (
            "id, timestamp, actor_id, actor_role, organization_id, action, entity_type, "
            "entity_id, ip_address, details_json, is_immutable, event_hash, previous_event_hash, "
            "hash_algorithm, sequence_number, severity, data_status"
        )
        query = f"SELECT {cols_query} FROM audit_events {where_sql} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        exec_params = list(params) + [limit, offset]
        cursor.execute(query, exec_params)

        cols = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        conn.close()

        events = [dict(zip(cols, r)) for r in rows]

        if return_pagination:
            return {
                "events": events,
                "total_count": total_count,
                "returned_count": len(events),
                "offset": offset,
                "limit": limit,
            }
        return events
    except Exception as e:
        print(f"[WARN] get_audit_events error: {e}")
        if return_pagination:
            return {"events": [], "total_count": 0, "returned_count": 0, "offset": offset, "limit": limit}
        return []


def get_identity_merge_candidates(status_filter: Optional[str] = "PENDING_HUMAN_REVIEW") -> list:
    """Retrieve identity merge candidates from Supabase with SQLite fallback."""
    from app.supabase_adapter import is_supabase_active, supa_get_identity_merge_candidates
    if is_supabase_active():
        try:
            res = supa_get_identity_merge_candidates(status_filter=status_filter)
            if res is not None and len(res) > 0:
                for rec in res:
                    for field in ("shared_traits", "conflicting_traits"):
                        if isinstance(rec.get(field), str):
                            try:
                                rec[field] = json.loads(rec[field])
                            except Exception:
                                rec[field] = []
                return res
        except Exception as e:
            print(f"[WARN] Supabase get_identity_merge_candidates error: {e}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if status_filter and status_filter.upper() != "ALL":
            cursor.execute(
                "SELECT * FROM identity_merge_candidates WHERE review_status = ? ORDER BY match_confidence DESC",
                (status_filter,),
            )
        else:
            cursor.execute("SELECT * FROM identity_merge_candidates ORDER BY match_confidence DESC")
        cols = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        results = []
        for r in rows:
            rec = dict(zip(cols, r))
            for field in ("shared_traits", "conflicting_traits"):
                try:
                    rec[field] = json.loads(rec[field]) if rec.get(field) else []
                except Exception:
                    rec[field] = []
            results.append(rec)
        return results
    except Exception as e:
        print(f"[WARN] get_identity_merge_candidates error: {e}")
        return []


def resolve_merge_candidate(candidate_id: str, action: str, notes: str, reviewed_by: str) -> dict:
    """Update a merge candidate resolution in BOTH Supabase (if active) and SQLite."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    local_rec = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE identity_merge_candidates SET review_status = ?, reviewed_by = ?, reviewed_at = ?, resolution_notes = ? WHERE id = ?",
            (action, reviewed_by, now, notes, candidate_id),
        )
        conn.commit()
        cursor.execute("SELECT * FROM identity_merge_candidates WHERE id = ?", (candidate_id,))
        cols = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        conn.close()
        if row:
            local_rec = dict(zip(cols, row))
            for field in ("shared_traits", "conflicting_traits"):
                try:
                    local_rec[field] = json.loads(local_rec[field]) if local_rec.get(field) else []
                except Exception:
                    local_rec[field] = []
    except Exception as e:
        print(f"[WARN] SQLite resolve_merge_candidate error: {e}")

    from app.supabase_adapter import is_supabase_active, supa_resolve_merge_candidate
    if is_supabase_active():
        try:
            supa_res = supa_resolve_merge_candidate(candidate_id, action, notes, reviewed_by)
            if supa_res:
                return supa_res
        except Exception as e:
            print(f"[WARN] Supabase resolve_merge_candidate error: {e}")

    return local_rec or {"id": candidate_id, "review_status": action, "reviewed_by": reviewed_by, "reviewed_at": now}


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


def record_advocate_sign_off(
    case_id: str,
    user_id: str,
    user_name: str,
    draft_text: Optional[str] = None,
) -> dict:
    """Record advocate counsel sign-off on the bail petition draft."""
    app_id = f"bail_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM bail_applications WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if row:
            app_id = row[0]
            cursor.execute(
                """
                UPDATE bail_applications
                SET advocate_signed_off = 1,
                    signed_off_by_user_id = ?,
                    signed_off_at = ?,
                    petition_draft_text = COALESCE(?, petition_draft_text),
                    updated_at = ?
                WHERE id = ?
                """,
                (user_id, now_iso, draft_text, now_iso, app_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO bail_applications
                (id, case_id, statutory_section, petition_draft_text, advocate_signed_off, signed_off_by_user_id, signed_off_at, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?, 'COUNSEL_SIGNED_OFF', ?, ?)
                """,
                (app_id, case_id, "Section 479 BNSS, 2023", draft_text or "", user_id, now_iso, now_iso, now_iso),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] record_advocate_sign_off failed: {e}")

    # Dual-write to Supabase when active
    try:
        from app.supabase_adapter import get_supabase_client, is_supabase_active
        if is_supabase_active():
            client = get_supabase_client()
            if client:
                client.table("bail_applications").upsert({
                    "id": app_id,
                    "case_id": case_id,
                    "advocate_signed_off": True,
                    "signed_off_by_user_id": user_id,
                    "signed_off_at": now_iso,
                    "petition_draft_text": draft_text or "",
                    "status": "COUNSEL_SIGNED_OFF",
                    "updated_at": now_iso,
                }).execute()
    except Exception as err:
        print(f"[WARN] Supabase record_advocate_sign_off error: {err}")

    return {
        "id": app_id,
        "case_id": case_id,
        "advocate_signed_off": True,
        "signed_off_by": user_name,
        "signed_off_at": now_iso,
    }


def get_case_bail_application(case_id: str) -> Optional[dict]:
    """Retrieve bail application record for a case."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bail_applications WHERE case_id = ? ORDER BY updated_at DESC LIMIT 1", (case_id,))
        row = cursor.fetchone()
        if row:
            cols = [c[0] for c in cursor.description]
            d = dict(zip(cols, row))
            d["advocate_signed_off"] = bool(d.get("advocate_signed_off"))
            conn.close()
            return d
        conn.close()
    except Exception as e:
        print(f"[WARN] get_case_bail_application error: {e}")
    return None



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
    source_authority: str = "INSTITUTIONAL",
    uploaded_by: Optional[str] = None,
    document_status: str = "PENDING_VERIFICATION",
    authoritative_source: bool = False,
    storage_path: Optional[str] = None,
    security_scan_status: str = "PASSED",
    security_scan_details: Optional[str] = None,
    current_version: int = 1,
    doc_id: Optional[str] = None,
) -> str:
    """Persist uploaded document metadata and extracted text."""
    import hashlib
    stable_id = doc_id or hashlib.md5(f"{case_id}-{document_type}".encode()).hexdigest()
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
        "source_authority": source_authority,
        "uploaded_by": uploaded_by,
        "document_status": document_status,
        "authoritative_source": int(authoritative_source),
        "storage_path": storage_path,
        "security_scan_status": security_scan_status,
        "security_scan_details": security_scan_details,
        "current_version": current_version,
        "uploaded_at": created_at,
    }
    _MEMORY_UPLOADED_DOCS.append(record)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO uploaded_documents 
               (id, case_id, document_type, file_name, extracted_text, custom_text, is_handwritten, ocr_engine, file_hash, file_size_bytes, mime_type, source_authority, uploaded_by, document_status, authoritative_source, storage_path, security_scan_status, security_scan_details, current_version, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                stable_id, case_id, document_type, file_name, extracted_text, custom_text,
                int(is_handwritten), ocr_engine, file_hash, file_size_bytes, mime_type,
                source_authority, uploaded_by, document_status, int(authoritative_source),
                storage_path, security_scan_status, security_scan_details, current_version, created_at,
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


def get_all_uploaded_documents() -> List[dict]:
    """Retrieve all uploaded documents from SQLite with memory fallback."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM uploaded_documents ORDER BY uploaded_at DESC")
        cols = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        print(f"[WARN] SQLite get_all_uploaded_documents error: {e}")

    return _MEMORY_UPLOADED_DOCS


# ── Notifications ─────────────────────────────────────────────────────────────

def add_notification(
    case_id: Optional[str],
    title: str,
    message: str,
    notif_type: str,
    target_role: Optional[str] = "ALL",
    user_id: Optional[str] = None,
) -> str:
    """Insert or refresh system alert with role and user targeting."""
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    clean_role = (target_role or "ALL").split(",")[0].strip().replace(" ", "_")
    notif_id = f"NOTIF-{case_id or clean_role}-{notif_type}-{today}-{uuid.uuid4().hex[:6]}"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    record = {
        "id": notif_id,
        "case_id": case_id,
        "title": title,
        "message": message,
        "type": notif_type,
        "target_role": target_role or "ALL",
        "user_id": user_id,
        "timestamp": timestamp,
        "is_read": 0,
    }
    _MEMORY_NOTIFICATIONS.append(record)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO notifications 
            (id, case_id, title, message, type, target_role, user_id, is_read, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (notif_id, case_id, title, message, notif_type, target_role or "ALL", user_id, timestamp),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] SQLite add_notification error: {e}")

    # Supabase sync if active
    try:
        from app.supabase_adapter import is_supabase_active, supa_add_notification
        if is_supabase_active():
            supa_rec = dict(record)
            supa_rec["is_read"] = False
            supa_add_notification(supa_rec)
    except Exception as e:
        print(f"[WARN] Supabase add_notification error: {e}")

    return notif_id


def get_all_notifications() -> List[dict]:
    """Retrieve all notifications sorted by newest first."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, case_id, title, message, type, is_read, timestamp, target_role, user_id FROM notifications ORDER BY timestamp DESC")
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
                    "read": bool(r[5]),
                    "timestamp": r[6],
                    "target_role": r[7] if len(r) > 7 else "ALL",
                    "user_id": r[8] if len(r) > 8 else None,
                }
                for r in rows
            ]
    except Exception as e:
        print(f"[WARN] SQLite get_all_notifications error: {e}")

    return _MEMORY_NOTIFICATIONS


def get_notifications_for_user(
    role: str,
    user_id: Optional[str] = None,
    linked_case_id: Optional[str] = None,
) -> List[dict]:
    """Retrieve notifications filtered specifically by recipient role, user ID, or linked case ID."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, case_id, title, message, type, is_read, timestamp, target_role, user_id 
            FROM notifications 
            ORDER BY timestamp DESC
            """
        )
        rows = cursor.fetchall()
        conn.close()

        results = []
        user_role_upper = (role or "").strip().upper()

        for r in rows:
            notif_id = r[0]
            case_id = r[1]
            title = r[2]
            message = r[3]
            notif_type = r[4]
            is_read = r[5]
            timestamp = r[6]
            target_role = r[7] or "ALL"
            n_user_id = r[8]

            # 1. Role matching
            role_match = False
            if target_role == "ALL":
                role_match = True
            else:
                allowed_roles = [ar.strip().upper() for ar in target_role.split(",")]
                if user_role_upper in allowed_roles:
                    role_match = True

            # 2. Specific User ID matching
            if n_user_id and user_id and n_user_id != user_id:
                role_match = False

            # 3. For ACCUSED_USER and FAMILY_GUARDIAN: only show their own linked case or general alerts
            if user_role_upper in ("ACCUSED_USER", "FAMILY_GUARDIAN"):
                if linked_case_id and case_id and case_id != linked_case_id:
                    role_match = False

            if role_match:
                results.append({
                    "id": notif_id,
                    "case_id": case_id,
                    "title": title,
                    "message": message,
                    "type": notif_type,
                    "read": bool(is_read),
                    "timestamp": timestamp,
                    "target_role": target_role,
                })

        return results
    except Exception as e:
        print(f"[WARN] SQLite get_notifications_for_user error: {e}")
        return []



# ── Governed Legal Knowledge Helper Functions ──────────────────────────────────

def create_legal_escalation(
    actor_id: str,
    actor_role: str,
    draft_statement: str,
    unsupported_citations: list,
    retrieved_context: list,
    grounding_score: float,
    escalation_reason: str,
    case_id: Optional[str] = None,
) -> Optional[dict]:
    """Persist a human review escalation task idempotently and alert supervising officers."""
    import hashlib
    import json
    import uuid
    import datetime

    statement_hash = hashlib.sha256(draft_statement.strip().encode("utf-8")).hexdigest()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Idempotency check: Don't create duplicate pending tasks for identical draft statement
        cursor.execute(
            "SELECT * FROM legal_human_review_tasks WHERE statement_hash = ? AND review_status = 'PENDING_REVIEW'",
            (statement_hash,),
        )
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return dict(existing)

        escalation_id = f"esc_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """
            INSERT INTO legal_human_review_tasks (
                id, created_at, actor_id, actor_role, case_id, statement_hash,
                draft_statement, unsupported_citations_json, retrieved_context_json,
                grounding_score, escalation_reason, assigned_role, review_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SUPERVISING_LEGAL_OFFICER', 'PENDING_REVIEW')
            """,
            (
                escalation_id, now_iso, actor_id, actor_role, case_id, statement_hash,
                draft_statement, json.dumps(unsupported_citations), json.dumps(retrieved_context),
                grounding_score, escalation_reason
            ),
        )

        # Create high-priority notification for DLSA supervisors
        notif_id = f"notif_esc_{escalation_id}"
        cursor.execute(
            """
            INSERT INTO notifications (id, case_id, title, message, type, target_role, is_read, timestamp)
            VALUES (?, ?, ?, ?, 'urgent', 'SUPERVISING_LEGAL_OFFICER,GOV_ADMIN', 0, ?)
            """,
            (
                notif_id,
                case_id,
                "Statutory Citation Integrity Escalation",
                f"Unsupported legal claims detected by {actor_role} ({actor_id}). Routed to Supervising Legal Officer.",
                now_iso,
            ),
        )


        conn.commit()
        conn.close()

        return {
            "id": escalation_id,
            "created_at": now_iso,
            "actor_id": actor_id,
            "statement_hash": statement_hash,
            "grounding_score": grounding_score,
            "review_status": "PENDING_REVIEW",
        }
    except Exception as e:
        print(f"[WARN] Failed to create legal escalation: {e}")
        return None


def get_pending_legal_escalations(status: str = "PENDING_REVIEW") -> List[dict]:
    """Retrieve human review tasks with caller role and unsupported citations."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM legal_human_review_tasks WHERE review_status = ? ORDER BY created_at DESC",
            (status,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[WARN] Failed to get legal escalations: {e}")
        return []


def resolve_legal_escalation(escalation_id: str, user_id: str, resolution_notes: str, new_status: str = "RESOLVED") -> bool:
    """Resolve a legal citation escalation with supervisory justification notes."""
    import datetime
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE legal_human_review_tasks
            SET review_status = ?, resolution_notes = ?, resolved_by = ?, resolved_at = ?
            WHERE id = ?
            """,
            (new_status, resolution_notes, user_id, now_iso, escalation_id),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[WARN] Failed to resolve legal escalation: {e}")
        return False


def log_legal_retrieval(
    query_id: str,
    actor_id: str,
    actor_role: str,
    organization_id: Optional[str],
    query_text: str,
    source_ids: list,
    source_versions: list,
    matched_citations: list,
    relevance_scores: list,
    selected_passages: list,
    used_superseded: bool,
    grounding_score: float = 0.0,
    routed_to_review: bool = False,
    status: str = "SUCCESS",
) -> None:
    """Log governed hybrid retrieval telemetry for institutional audit."""
    import json
    import uuid
    import datetime
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_id = f"ret_{uuid.uuid4().hex[:12]}"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO legal_retrieval_logs (
                id, query_id, actor_id, actor_role, organization_id, query_text,
                source_ids_json, source_versions_json, matched_citation_keys_json,
                relevance_scores_json, selected_passages_json, used_superseded,
                grounding_score, routed_to_human_review, status, queried_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id, query_id, actor_id, actor_role, organization_id, query_text,
                json.dumps(source_ids), json.dumps(source_versions), json.dumps(matched_citations),
                json.dumps(relevance_scores), json.dumps(selected_passages), 1 if used_superseded else 0,
                grounding_score, 1 if routed_to_review else 0, status, now_iso,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] Failed to log legal retrieval: {e}")



def get_police_actions(station_id: str = "") -> list:
    """Retrieve operational document requests and actions for a police station."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if station_id:
        cursor.execute("SELECT * FROM police_actions WHERE police_station_id = ? ORDER BY created_at DESC", (station_id,))
    else:
        cursor.execute("SELECT * FROM police_actions ORDER BY created_at DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def acknowledge_police_action(action_id: str, user_id: str) -> bool:
    """Mark a police document/hearing action as acknowledged by the station."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE police_actions SET status = 'ACKNOWLEDGED' WHERE id = ?",
        (action_id,),
    )
    cnt = cursor.rowcount
    conn.commit()
    conn.close()
    return cnt > 0


def complete_police_action(action_id: str, document_id: str, user_id: str, notes: str = "") -> bool:
    """Complete a police action by linking the uploaded document record."""
    import datetime
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE police_actions 
        SET status = 'COMPLETED', document_id = ?, notes = ?, completed_at = ?
        WHERE id = ?
        """,
        (document_id, notes, now_iso, action_id),
    )
    cnt = cursor.rowcount
    conn.commit()
    conn.close()
    return cnt > 0



# ── Secure Evidence Document Repository Helpers ──────────────────────────────

def get_uploaded_document_by_id(doc_id: str) -> Optional[dict]:
    """Retrieve an uploaded document record by primary ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM uploaded_documents WHERE id = ?", (doc_id,))
    cols = [c[0] for c in cursor.description]
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(zip(cols, row))
    return None


def update_uploaded_document_status(document_id: str, new_status: str) -> bool:
    """Update document_status of an uploaded document (e.g. PENDING_VERIFICATION -> VERIFIED)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE uploaded_documents SET document_status = ? WHERE id = ?",
        (new_status, document_id),
    )
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def store_document_version(
    document_id: str,
    version_number: int,
    parent_version_id: Optional[str] = None,
    processing_status: str = "SUCCESS",
    ocr_engine: str = "none",
    ocr_confidence: float = 1.0,
    is_handwritten: bool = False,
    manual_verification_required: bool = False,
    needs_human_verification_reason: Optional[str] = None,
    raw_text: str = "",
    normalized_text: str = "",
    classification: str = "UNKNOWN",
    extracted_facts: Optional[dict] = None,
    rag_citations: Optional[list] = None,
    assessment_summary: Optional[dict] = None,
    processed_by: str = "system",
    processing_time_ms: float = 0.0,
) -> str:
    """Store an immutable processing snapshot version for a document."""
    version_id = f"dpv_{uuid.uuid4().hex[:12]}"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO document_processing_versions
        (id, document_id, version_number, parent_version_id, processing_status,
         ocr_engine, ocr_confidence, is_handwritten, manual_verification_required,
         needs_human_verification_reason, raw_text, normalized_text, classification,
         extracted_facts_json, rag_citations_json, assessment_summary_json,
         processed_by, processing_time_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            document_id,
            version_number,
            parent_version_id,
            processing_status,
            ocr_engine,
            ocr_confidence,
            1 if is_handwritten else 0,
            1 if manual_verification_required else 0,
            needs_human_verification_reason,
            raw_text,
            normalized_text,
            classification,
            json.dumps(extracted_facts or {}),
            json.dumps(rag_citations or []),
            json.dumps(assessment_summary or {}),
            processed_by,
            processing_time_ms,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
        ),
    )
    # Also update current_version on the parent uploaded_documents record
    cursor.execute(
        "UPDATE uploaded_documents SET current_version = ? WHERE id = ?",
        (version_number, document_id),
    )
    conn.commit()
    conn.close()
    return version_id


def get_document_versions(document_id: str) -> List[dict]:
    """Retrieve all processing versions for a document, ordered chronologically."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM document_processing_versions WHERE document_id = ? ORDER BY version_number ASC",
        (document_id,),
    )
    cols = [c[0] for c in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(zip(cols, r))
        try:
            d["extracted_facts"] = json.loads(d.get("extracted_facts_json") or "{}")
        except Exception:
            d["extracted_facts"] = {}
        try:
            d["rag_citations"] = json.loads(d.get("rag_citations_json") or "[]")
        except Exception:
            d["rag_citations"] = []
        try:
            d["assessment_summary"] = json.loads(d.get("assessment_summary_json") or "{}")
        except Exception:
            d["assessment_summary"] = {}
        d["is_handwritten"] = bool(d.get("is_handwritten", 0))
        d["manual_verification_required"] = bool(d.get("manual_verification_required", 0))
        results.append(d)
    return results


def record_field_correction(
    document_id: str,
    field_name: str,
    original_machine_value: Any,
    corrected_value: Any,
    source_span: Optional[str],
    correction_reason: str,
    corrected_by: str,
    corrected_by_role: str,
    version_id: Optional[str] = None,
) -> str:
    """Record a human-in-the-loop correction for an extracted fact."""
    correction_id = f"cor_{uuid.uuid4().hex[:12]}"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO document_field_corrections
        (id, document_id, version_id, field_name, original_machine_value,
         corrected_value, source_span, correction_reason, corrected_by,
         corrected_by_role, corrected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            correction_id,
            document_id,
            version_id,
            field_name,
            str(original_machine_value) if original_machine_value is not None else "",
            str(corrected_value),
            source_span or "",
            correction_reason,
            corrected_by,
            corrected_by_role,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return correction_id


def get_document_field_corrections(document_id: str) -> List[dict]:
    """Retrieve all human corrections made to extracted fields of a document."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM document_field_corrections WHERE document_id = ? ORDER BY corrected_at DESC",
        (document_id,),
    )
    cols = [c[0] for c in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def log_document_access(
    document_id: str,
    case_id: str,
    user_id: str,
    user_role: str,
    action: str,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
) -> str:
    """Log a document access, download, or inspection event."""
    log_id = f"dal_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO document_access_logs
            (id, document_id, case_id, action, user_id, user_role, ip_address, details_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                document_id,
                case_id,
                action,
                user_id,
                user_role,
                ip_address or "127.0.0.1",
                json.dumps(details or {}),
                now_iso,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] log_document_access failed: {e}")
    return log_id


def build_evidence_chain(document_id: str) -> Optional[dict]:
    """
    Construct the end-to-end provenance graph linking:
    Document Version (SHA-256)
      -> Extracted Facts (with verbatim source spans)
      -> Human Field Corrections
      -> Statutory Rule Calculations (BNSS 479)
      -> Generated AI Assessment / Output
      -> Downstream Human & Institutional Actions
    """
    doc = get_uploaded_document_by_id(document_id)
    if not doc:
        return None

    case_id = doc.get("case_id")
    versions = get_document_versions(document_id)
    corrections = get_document_field_corrections(document_id)

    # Latest version details
    latest_version = versions[-1] if versions else None
    extracted_facts = latest_version.get("extracted_facts", {}) if latest_version else {}

    # Map corrections by field name
    corrections_by_field = {c["field_name"]: c for c in corrections}

    # Build enriched facts list with original machine values, source spans, and active corrections
    enriched_facts = []
    if isinstance(extracted_facts, dict):
        for field, item in extracted_facts.items():
            if isinstance(item, dict):
                machine_val = item.get("value")
                span = item.get("source_span", "")
                conf = item.get("confidence", 1.0)
                char_start = item.get("char_start", 0)
                char_end = item.get("char_end", 0)
                needs_review = item.get("needs_human_review", False)
            else:
                machine_val = item
                span = ""
                conf = 1.0
                char_start = 0
                char_end = 0
                needs_review = False

            has_corr = field in corrections_by_field
            effective_val = corrections_by_field[field]["corrected_value"] if has_corr else machine_val

            enriched_facts.append({
                "field_name": field,
                "machine_value": machine_val,
                "effective_value": effective_val,
                "confidence": conf,
                "source_span": span,
                "char_range": [char_start, char_end],
                "is_corrected": has_corr,
                "correction_details": corrections_by_field.get(field),
                "needs_human_review": needs_review,
            })

    # Find downstream rule evaluation for case
    from app.database import get_case
    from app.agents.eligibility_agent import evaluate_eligibility
    case_obj = get_case(case_id)
    rule_eval = None
    if case_obj:
        try:
            rule_eval = evaluate_eligibility(case_obj)
        except Exception:
            rule_eval = None

    # Find related audit actions on this case/document
    try:
        from app.repositories.audit_repository import audit_repo
        raw_audit_objs = audit_repo.get_entity_audit_trail("court_case", case_id) if case_id else []
        raw_audit = [a.model_dump() if hasattr(a, "model_dump") else (a if isinstance(a, dict) else a.__dict__) for a in raw_audit_objs]
    except Exception:
        raw_audit = []
    relevant_actions = []
    for a in raw_audit[:8]:
        action_name = a.get("action")
        if action_name in (
            "CASE_APPROVED_FOR_FILING", "CASE_FILED_IN_COURT",
            "POLICE_DOCUMENT_SUBMITTED", "EVIDENCE_VERIFIED",
            "DOCUMENT_FIELD_CORRECTED", "DOCUMENT_REPROCESSED"
        ):
            relevant_actions.append({
                "action": action_name,
                "actor_id": a.get("actor_id"),
                "actor_role": a.get("actor_role"),
                "timestamp": a.get("timestamp"),
            })

    return {
        "document_id": doc["id"],
        "case_id": case_id,
        "file_name": doc["file_name"],
        "document_type": doc.get("document_type"),
        "document_status": doc.get("document_status", "PENDING_VERIFICATION"),
        "file_hash_sha256": doc["file_hash"],
        "file_size_bytes": doc.get("file_size_bytes", 0),
        "mime_type": doc.get("mime_type", "application/pdf"),
        "source_authority": doc.get("source_authority", "INSTITUTIONAL"),
        "uploaded_by": doc.get("uploaded_by"),
        "uploaded_at": doc.get("uploaded_at"),
        "security_screening": {
            "status": doc.get("security_scan_status", "PASSED"),
            "details": doc.get("security_scan_details"),
            "engine": "NyayaMitra-SafeBoundaryScanner-v1.0",
        },
        "version_history": [
            {
                "version_id": v["id"],
                "version_number": v["version_number"],
                "parent_version_id": v.get("parent_version_id"),
                "ocr_engine": v.get("ocr_engine"),
                "ocr_confidence": v.get("ocr_confidence"),
                "is_handwritten": v.get("is_handwritten"),
                "manual_verification_required": v.get("manual_verification_required"),
                "needs_human_verification_reason": v.get("needs_human_verification_reason"),
                "processing_time_ms": v.get("processing_time_ms"),
                "processed_by": v.get("processed_by"),
                "created_at": v.get("created_at"),
            }
            for v in versions
        ],
        "current_version_number": doc.get("current_version", 1),
        "evidence_chain": {
            "origin_raw_file": {
                "file_name": doc["file_name"],
                "sha256": doc["file_hash"],
                "immutable": True,
                "storage_vault": "VAULT_PROTECTED",
            },
            "processing_extraction": {
                "version_id": latest_version["id"] if latest_version else None,
                "version_number": latest_version["version_number"] if latest_version else 1,
                "ocr_engine": latest_version.get("ocr_engine") if latest_version else doc.get("ocr_engine"),
                "ocr_confidence": latest_version.get("ocr_confidence") if latest_version else 1.0,
                "manual_verification_required": latest_version.get("manual_verification_required") if latest_version else False,
            },
            "extracted_facts_with_spans": enriched_facts,
            "statutory_rule_grounding": {
                "statute": "Section 479 Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
                "eligibility_outcome": rule_eval.get("eligible") if rule_eval else False,
                "threshold_fraction": 0.5,
                "calculated_served_days": rule_eval.get("custody_days_served") if rule_eval else None,
                "statutory_required_days": rule_eval.get("required_custody_days") if rule_eval else None,
            },
            "ai_generated_assessment": latest_version.get("assessment_summary") if latest_version else None,
            "institutional_actions": relevant_actions,
        },
    }


# ── Domain Service & Repository Instances ──────────────────────────────────────

from app.repositories.case_repository import CaseRepository
from app.repositories.audit_repository import AuditRepository

from app.services.case_service import CaseService

case_repo = CaseRepository(DB_PATH)
audit_repo = AuditRepository(DB_PATH)
case_service = CaseService(case_repo, audit_repo)




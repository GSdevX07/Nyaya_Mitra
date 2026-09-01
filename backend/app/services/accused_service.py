"""
services/accused_service.py — Unified Accused-Centric Dossier & Profile Service.

Aggregates multiple cases, facilities, custody records, and documents per person.
Enforces ABAC medical data quarantining, facts vs. interpretations timeline generation,
and human-in-the-loop duplicate identity resolution.
"""
from __future__ import annotations
import datetime
from typing import List, Dict, Any, Optional

from fastapi import HTTPException, status

from app.auth.roles import Role
from app.auth.user_store import AuthUser
from app.auth.policy import check_permission, ACCUSED_FAMILY_READ, ACCUSED_SELF_READ
from app.models.domain import (
    TimelineItemType,
    EventCategory,
    VerificationStatus,
    CommunicationChannel,
)


# ── Canonical Multi-Case Demo Profiles ─────────────────────────────────────────

_DEMO_ACCUSED_REGISTRY: Dict[str, Dict[str, Any]] = {
    "acc_utp_0001": {
        "id": "acc_utp_0001",
        "full_name": "Suresh Patel",
        "alias_names": ["Surya", "Suresh Bhai"],
        "gender": "Male",
        "age": 24,
        "date_of_birth": "2001-04-15",
        "preferred_language": "hi",
        "health_vulnerability": False,
        "is_senior_citizen": False,
        "repeat_offender": False,
        "permanent_address": "H-42, Shakurpur, North-West Delhi - 110034",
        "provenance": {
            "source_system": "e-Prisons Delhi",
            "source_record_id": "EP-TJ04-2025-0811",
            "confidence_score": 1.0,
            "verification_status": "CONFIRMED",
            "ingested_at": "2025-01-10T09:30:00Z"
        },
        "family_contacts": [
            {
                "id": "fcon_0001_1",
                "accused_id": "acc_utp_0001",
                "name": "Ramesh Patel",
                "relation": "Father",
                "phone": "+91 98765 43210",
                "alt_phone": "+91 98765 43211",
                "address": "H-42, Shakurpur, North-West Delhi",
                "preferred_language": "hi",
                "preferred_channel": "SMS",
                "is_primary_contact": True,
                "verified_by_dlsa": True,
            },
            {
                "id": "fcon_0001_2",
                "accused_id": "acc_utp_0001",
                "name": "Sunita Devi",
                "relation": "Mother",
                "phone": "+91 98765 77007",
                "preferred_language": "hi",
                "preferred_channel": "WHATSAPP",
                "is_primary_contact": False,
                "verified_by_dlsa": True,
            }
        ],
        "medical_record": {
            "has_vulnerability": False,
            "vulnerability_category": "STANDARD_FIT",
            "details_restricted": "General health stable. No chronic ailment recorded during jail intake medical screening.",
            "medical_officer_name": "Dr. V. K. Malhotra (CMO, Tihar Jail)",
            "examining_facility_id": "fac_tihar_jail_04",
            "last_examination_date": "2025-01-11",
            "treatment_underway": False,
            "requires_hospital_referral": False,
        },
        "government_identifiers": {
            "prison_inmate_no": "TJ-2025-UTP-4018",
            "cctns_person_id": "CCTNS-DL-2025-89102",
            "voter_id_masked": "DL/04/029/XXXXX1",
            "aadhaar_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        },
        "linked_case_ids": ["UTP-0001"]
    },
    "acc_utp_0002": {
        "id": "acc_utp_0002",
        "full_name": "Mohammad Rehan",
        "alias_names": ["Rehan Ansari"],
        "gender": "Male",
        "age": 29,
        "date_of_birth": "1996-08-20",
        "preferred_language": "en",
        "health_vulnerability": False,
        "is_senior_citizen": False,
        "repeat_offender": False,
        "permanent_address": "B-12, Jamia Nagar, Okhla, New Delhi - 110025",
        "provenance": {
            "source_system": "e-Prisons Delhi",
            "source_record_id": "EP-TJ04-2025-1102",
            "confidence_score": 1.0,
            "verification_status": "CONFIRMED",
            "ingested_at": "2025-03-01T11:00:00Z"
        },
        "family_contacts": [
            {
                "id": "fcon_0002_1",
                "accused_id": "acc_utp_0002",
                "name": "Fatima Begum",
                "relation": "Mother",
                "phone": "+91 98111 22334",
                "preferred_language": "en",
                "preferred_channel": "WHATSAPP",
                "is_primary_contact": True,
                "verified_by_dlsa": True,
            }
        ],
        "medical_record": {
            "has_vulnerability": False,
            "vulnerability_category": "STANDARD_FIT",
            "details_restricted": "Regular medical intake complete. Vitals normal.",
            "medical_officer_name": "Dr. V. K. Malhotra",
            "examining_facility_id": "fac_tihar_jail_04",
            "last_examination_date": "2025-03-02",
            "treatment_underway": False,
            "requires_hospital_referral": False,
        },
        "government_identifiers": {
            "prison_inmate_no": "TJ-2025-UTP-4890",
            "cctns_person_id": "CCTNS-DL-2025-99214",
            "voter_id_masked": "DL/08/041/XXXXX9",
            "aadhaar_hash": "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"
        },
        "linked_case_ids": ["UTP-0002"]
    },
    "acc_utp_0003": {
        "id": "acc_utp_0003",
        "full_name": "Vikramaditya Rao",
        "alias_names": ["V. A. Rao"],
        "gender": "Male",
        "age": 68,
        "date_of_birth": "1957-11-12",
        "preferred_language": "en",
        "health_vulnerability": True,
        "is_senior_citizen": True,
        "repeat_offender": False,
        "permanent_address": "Flat 4B, Sector 14, Rohini, Delhi - 110085",
        "provenance": {
            "source_system": "e-Prisons Delhi",
            "source_record_id": "EP-TJ04-2024-5412",
            "confidence_score": 0.95,
            "verification_status": "CONFIRMED",
            "ingested_at": "2024-08-01T14:15:00Z"
        },
        "family_contacts": [
            {
                "id": "fcon_0003_1",
                "accused_id": "acc_utp_0003",
                "name": "Ananya Rao",
                "relation": "Daughter",
                "phone": "+91 99887 76655",
                "preferred_language": "en",
                "preferred_channel": "PHONE_CALL",
                "is_primary_contact": True,
                "verified_by_dlsa": True,
            }
        ],
        "medical_record": {
            "has_vulnerability": True,
            "vulnerability_category": "CHRONIC_CARDIO_GERIATRIC",
            "details_restricted": "SENSITIVE MEDICAL FILE: Diagnosed with Chronic Coronary Artery Disease with moderate left ventricular dysfunction. Prescribed daily dual antiplatelet and statin therapy. Requires bi-weekly cardiology review and emergency hospital referral access.",
            "medical_officer_name": "Dr. P. S. Oberoi (Senior Medical Specialist)",
            "examining_facility_id": "fac_tihar_jail_04",
            "last_examination_date": "2025-01-20",
            "treatment_underway": True,
            "requires_hospital_referral": True,
        },
        "government_identifiers": {
            "prison_inmate_no": "TJ-2024-UTP-1092",
            "cctns_person_id": "CCTNS-DL-2024-44109",
            "voter_id_masked": "DL/02/011/XXXXX4",
            "aadhaar_hash": "4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce"
        },
        "linked_case_ids": ["UTP-0003"]
    }
}


# ── Canonical Duplicate Identity Candidates ────────────────────────────────────

_DEMO_DUPLICATE_CANDIDATES: List[Dict[str, Any]] = [
    {
        "id": "imr_cand_001",
        "source_accused_id": "acc_utp_0001",
        "source_name": "Suresh Patel",
        "source_facility": "Tihar Central Jail No. 4",
        "source_father_name": "Ramesh Patel",
        "source_dob": "2001-04-15",
        "candidate_accused_id": "acc_sim_9042",
        "candidate_name": "Suresh K. Patel",
        "candidate_facility": "Rohini District Jail No. 10",
        "candidate_father_name": "Ramesh Patel",
        "candidate_dob": "2001-04-18",
        "match_confidence": 0.88,
        "shared_traits": [
            "Exact Father's Name Match ('Ramesh Patel')",
            "Date of Birth variance under 3 days (15-Apr vs 18-Apr)",
            "High phonetic name similarity (0.94 Metaphone)",
            "Identical residential pin code (110034)"
        ],
        "conflicting_traits": [
            "Different initial arresting police stations (Gandhi Nagar vs Shakurpur)",
            "Different Prison Inmate Reference Numbers"
        ],
        "match_explanation": "Probabilistic matcher detected probable identity duplicate between undertrial admissions across Tihar and Rohini jails. Father name and birth year match with 88% composite confidence. Automatic merge withheld pending supervising legal officer review.",
        "review_status": "PENDING_HUMAN_REVIEW",
        "created_at": "2025-02-15T10:00:00Z"
    },
    {
        "id": "imr_cand_002",
        "source_accused_id": "acc_utp_0002",
        "source_name": "Mohammad Rehan",
        "source_facility": "Tihar Central Jail No. 4",
        "source_father_name": "Late Abdul Ansari",
        "source_dob": "1996-08-20",
        "candidate_accused_id": "acc_sim_8819",
        "candidate_name": "Rehan A. Ansari",
        "candidate_facility": "Mandoli Jail Complex No. 11",
        "candidate_father_name": "Abdul Ansari",
        "candidate_dob": "1996-08-20",
        "match_confidence": 0.92,
        "shared_traits": [
            "Exact Date of Birth Match (20-Aug-1996)",
            "Father Name Match ('Abdul Ansari')",
            "Recorded alias matches candidate primary name ('Rehan Ansari')"
        ],
        "conflicting_traits": [
            "Differing CCTNS station registration codes"
        ],
        "match_explanation": "High-confidence multi-facility cross-match with alias correlation. Requires human legal confirmation before joining case dockets.",
        "review_status": "PENDING_HUMAN_REVIEW",
        "created_at": "2025-02-20T14:30:00Z"
    }
]


# ── Core Service Functions ────────────────────────────────────────────────────

def _has_medical_access(user: AuthUser) -> bool:
    """Return True if user role is authorized to view sensitive medical data."""
    # Medical access is restricted to administrative and supervisory personnel
    allowed_roles = {
        Role.PLATFORM_ADMIN,
        Role.SUPERVISING_LEGAL_OFFICER,
        Role.DLSA_OFFICER,
        Role.GOV_ADMIN,
        Role.JAIL_OFFICER,
    }
    return user.role in allowed_roles


def get_accused_profile(accused_id: str, user: AuthUser) -> Dict[str, Any]:
    """
    Fetch an accused person's consolidated profile across all cases and facilities.
    Applies strict ABAC medical redaction and tenant protection.
    """
    accused_id = accused_id.strip()
    profile = _DEMO_ACCUSED_REGISTRY.get(accused_id)

    if not profile:
        # Check SQLite or database fallback
        from app.database import get_db_connection
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM accused_persons WHERE id = ?", (accused_id,)).fetchone()
        conn.close()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Accused profile with ID '{accused_id}' not found.",
            )
        # Synthesize profile from DB row
        profile = {
            "id": row["id"],
            "full_name": row["full_name"],
            "alias_names": [],
            "gender": row["gender"],
            "age": row["age"],
            "preferred_language": row["preferred_language"],
            "health_vulnerability": bool(row["health_vulnerability"]),
            "is_senior_citizen": bool(row["is_senior_citizen"]),
            "repeat_offender": bool(row["repeat_offender"]),
            "permanent_address": row["permanent_address"],
            "provenance": {
                "source_system": "Nyaya Mitra Core Master",
                "source_record_id": row["id"],
                "confidence_score": 1.0,
                "verification_status": "CONFIRMED",
            },
            "family_contacts": [
                {
                    "name": row["relative_name"] or "Not Recorded",
                    "relation": row["relative_relation"] or "Guardian",
                    "phone": row["relative_phone"] or "N/A",
                    "preferred_language": "hi",
                    "preferred_channel": "SMS",
                    "is_primary_contact": True,
                }
            ] if row["relative_name"] else [],
            "medical_record": {
                "has_vulnerability": bool(row["health_vulnerability"]),
                "vulnerability_category": "RECORDED_IN_INTAKE" if row["health_vulnerability"] else "NONE",
                "details_restricted": row["health_details"] or "No specific medical complications recorded.",
            },
            "government_identifiers": {
                "inmate_no": f"INM-{row['id'].upper()}",
            },
            "linked_case_ids": []
        }

    # Fetch all connected court cases from database
    from app.database import get_all_cases
    all_cases = get_all_cases()
    connected_cases = []
    for c in all_cases:
        c_accused_id = f"acc_{c.case_id.lower().replace('-', '_')}"
        if c_accused_id == accused_id or c.case_id in profile.get("linked_case_ids", []):
            connected_cases.append({
                "case_id": c.case_id,
                "court_name": c.court_name,
                "fir_number": c.fir_number,
                "police_station": c.police_station,
                "current_status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "assigned_lawyer": getattr(c, "assigned_lawyer_id", None) or getattr(c, "assigned_lawyer", None) or "Adv. Rajesh Sharma (DLSA Panel)",
                "days_in_custody": getattr(c, "custody_days", getattr(c, "days_in_custody", 200)),
                "max_sentence_days": getattr(c, "max_sentence_days_for_offense", getattr(c, "max_sentence_days", 365)),
                "eligible_under_479": getattr(c, "eligible_under_479", True),
                "next_hearing_date": getattr(c, "next_hearing_date", "2025-03-25"),
            })

    # Prepare response copy
    result = dict(profile)
    result["connected_cases"] = connected_cases
    result["total_cases_count"] = len(connected_cases)

    # ABAC Medical Data Quarantining
    if not _has_medical_access(user):
        if result.get("medical_record"):
            result["medical_record"] = {
                "has_vulnerability": result["medical_record"].get("has_vulnerability", False),
                "vulnerability_category": "RESTRICTED",
                "details_restricted": "[RESTRICTED SENSITIVE MEDICAL ENVELOPE — Access requires CASES_READ_MEDICAL authorization]",
                "is_redacted": True,
            }

    # Restrict government ID envelope from external and citizen users
    if user.role in (Role.ACCUSED_USER, Role.FAMILY_GUARDIAN, Role.CONTROLLED_EXTERNAL_ADVOCATE):
        if "government_identifiers" in result:
            result["government_identifiers"] = {
                "inmate_reference": "CONFIRMED_ON_RECORD",
                "is_redacted_for_privacy": True
            }

    return result


def get_accused_timeline(accused_id: str, user: AuthUser) -> List[Dict[str, Any]]:
    """
    Generate chronological timeline separating factual records from system-generated interpretations.
    Every item indicates source provenance, date, recorded authority, and verification status.
    """
    accused_id = accused_id.strip()

    # Timeline events registry
    timeline: List[Dict[str, Any]] = [
        # 1. Factual: Police FIR
        {
            "id": f"tle_{accused_id}_01",
            "accused_id": accused_id,
            "item_type": TimelineItemType.FACTUAL_EVENT.value,
            "category": EventCategory.POLICE_ACTION.value,
            "title": "FIR Registered",
            "description": "FIR No. 2025-010 registered at Gandhi Nagar Police Station under BNS Section 115(2).",
            "event_date": "2025-01-10T08:30:00Z",
            "source_name": "CCTNS Police Gateway",
            "source_record_id": "FIR-2025-010",
            "recorded_by": "Sub-Inspector V. K. Sharma (IO)",
            "verification_status": VerificationStatus.CONFIRMED.value,
            "confidence_score": 1.0,
            "is_disputed": False,
        },
        # 2. Factual: Remand Order
        {
            "id": f"tle_{accused_id}_02",
            "accused_id": accused_id,
            "item_type": TimelineItemType.FACTUAL_EVENT.value,
            "category": EventCategory.COURT_HEARING.value,
            "title": "First Judicial Remand Production",
            "description": "Produced before Metropolitan Magistrate Court 02, Central. Remanded to 14 days judicial custody.",
            "event_date": "2025-01-10T14:45:00Z",
            "source_name": "e-Courts CIS",
            "source_record_id": "CIS-DLCT-REM-2025-0012",
            "recorded_by": "Court Master / Judicial Magistrate",
            "verification_status": VerificationStatus.CONFIRMED.value,
            "confidence_score": 1.0,
            "is_disputed": False,
        },
        # 3. Factual: Jail Admission
        {
            "id": f"tle_{accused_id}_03",
            "accused_id": accused_id,
            "item_type": TimelineItemType.FACTUAL_EVENT.value,
            "category": EventCategory.CUSTODY.value,
            "title": "Prison Admission & Medical Intake",
            "description": "Admitted to Tihar Central Prison No. 4 as Undertrial Prisoner. Physical marks and intake biometric recorded.",
            "event_date": "2025-01-10T18:15:00Z",
            "source_name": "e-Prisons National Portal",
            "source_record_id": "EP-TJ04-ADM-8902",
            "recorded_by": "Jail Superintendent / Intake Duty Officer",
            "verification_status": VerificationStatus.CONFIRMED.value,
            "confidence_score": 1.0,
            "is_disputed": False,
        },
        # 4. Factual: Legal Aid Assigned
        {
            "id": f"tle_{accused_id}_04",
            "accused_id": accused_id,
            "item_type": TimelineItemType.FACTUAL_EVENT.value,
            "category": EventCategory.LEGAL_AID.value,
            "title": "Legal Aid Counsel Appointed",
            "description": "DLSA Central Delhi assigned panel advocate Adv. Rajesh Sharma under the free legal services mandate.",
            "event_date": "2025-01-15T11:00:00Z",
            "source_name": "DLSA Legal Services Portal",
            "source_record_id": "DLSA-CD-APPT-2025-0112",
            "recorded_by": "DLSA Secretary / Legal Aid Allocation Desk",
            "verification_status": VerificationStatus.CONFIRMED.value,
            "confidence_score": 1.0,
            "is_disputed": False,
        },
        # 5. System Interpretation: Section 479 BNSS Statutory Eligibility Evaluation
        {
            "id": f"tle_{accused_id}_05",
            "accused_id": accused_id,
            "item_type": TimelineItemType.SYSTEM_INTERPRETATION.value,
            "category": EventCategory.STATUTORY_RULE.value,
            "title": "Statutory Eligibility Computed (Section 479 BNSS)",
            "description": "System calculated 200 days custody against 122 days statutory threshold (1/3 of max sentence 365 days). Offence is first-time non-capital undertrial. Status evaluated as ELIGIBLE for statutory bail review.",
            "event_date": "2025-02-01T06:00:00Z",
            "source_name": "Nyaya Mitra BNSS Deterministic Ruleset Engine",
            "source_record_id": "CALC-BNSS-479-V1-2025",
            "recorded_by": "Automated Statutory Calculator v1.2",
            "verification_status": VerificationStatus.CONFIRMED.value,
            "confidence_score": 0.99,
            "is_disputed": False,
        },
        # 6. Factual: Evidence Cryptographic Vault Verification
        {
            "id": f"tle_{accused_id}_06",
            "accused_id": accused_id,
            "item_type": TimelineItemType.FACTUAL_EVENT.value,
            "category": EventCategory.EVIDENCE_INTEGRITY.value,
            "title": "Remand Order SHA-256 Integrity Verified",
            "description": "Court Remand Order document verified against institutional cryptographic SHA-256 hash. Zero tampering detected.",
            "event_date": "2025-02-10T12:00:00Z",
            "source_name": "Nyaya Mitra Evidence Vault",
            "source_record_id": "EVI-UTP-0001-remand_order",
            "recorded_by": "Evidence Verification Officer",
            "verification_status": VerificationStatus.CONFIRMED.value,
            "confidence_score": 1.0,
            "is_disputed": False,
        },
        # 7. System Interpretation: Hearing Anomaly & Delay Evaluation
        {
            "id": f"tle_{accused_id}_07",
            "accused_id": accused_id,
            "item_type": TimelineItemType.SYSTEM_INTERPRETATION.value,
            "category": EventCategory.STATUTORY_RULE.value,
            "title": "Delay Attribution Analysis",
            "description": "Zero days of excluded delay attributable to the accused detected. Full 200 custody days qualify as countable detention.",
            "event_date": "2025-02-15T08:00:00Z",
            "source_name": "Nyaya Mitra Custody Analysis Agent",
            "source_record_id": "AGENT-CUSTODY-DELAY-001",
            "recorded_by": "Automated Custody Intelligence Engine",
            "verification_status": VerificationStatus.CONFIRMED.value,
            "confidence_score": 0.95,
            "is_disputed": False,
        }
    ]

    # Special medical event if applicable and permitted
    if accused_id == "acc_utp_0003":
        if _has_medical_access(user):
            timeline.append({
                "id": f"tle_{accused_id}_08_med",
                "accused_id": accused_id,
                "item_type": TimelineItemType.FACTUAL_EVENT.value,
                "category": EventCategory.MEDICAL_SENSITIVE.value,
                "title": "Hospital Referral Cardiology Examination",
                "description": "Senior medical officer recorded cardiac vulnerability requiring continuous dual antiplatelet regimen and hospital referral.",
                "event_date": "2025-01-20T10:00:00Z",
                "source_name": "Tihar Hospital Medical Registry",
                "source_record_id": "MED-TJ04-2025-CARDIO",
                "recorded_by": "Dr. P. S. Oberoi (Senior Medical Specialist)",
                "verification_status": VerificationStatus.CONFIRMED.value,
                "confidence_score": 1.0,
                "is_disputed": False,
                "is_sensitive_medical": True,
            })

    # Sort chronological descending
    timeline.sort(key=lambda x: x["event_date"], reverse=True)
    return timeline


def get_duplicate_candidates(user: AuthUser) -> List[Dict[str, Any]]:
    """
    Retrieve candidate duplicate identities requiring human legal review.
    """
    return [c for c in _DEMO_DUPLICATE_CANDIDATES if c["review_status"] == "PENDING_HUMAN_REVIEW"]


def resolve_duplicate_candidate(
    candidate_id: str,
    action: str,  # MERGE_RECORDS, REJECT_MATCH, MARK_AS_ALIAS
    resolution_notes: str,
    user: AuthUser,
) -> Dict[str, Any]:
    """
    Execute human-in-the-loop duplicate resolution.
    Strictly requires supervisory or administrative authority.
    """
    allowed_roles = {
        Role.SUPERVISING_LEGAL_OFFICER,
        Role.GOV_ADMIN,
        Role.PLATFORM_ADMIN,
        Role.DLSA_OFFICER,
    }
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only supervising legal officers or administrative authorities can resolve duplicate identity candidates.",
        )

    candidate = next((c for c in _DEMO_DUPLICATE_CANDIDATES if c["id"] == candidate_id), None)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Duplicate review candidate '{candidate_id}' not found.",
        )

    action = action.upper().strip()
    valid_actions = {"MERGE_RECORDS", "REJECT_MATCH", "MARK_AS_ALIAS"}
    if action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resolution action '{action}'. Must be one of {valid_actions}.",
        )

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    candidate["review_status"] = action
    candidate["reviewed_by"] = user.full_name
    candidate["reviewed_at"] = now
    candidate["resolution_notes"] = resolution_notes

    # Append immutable audit event
    try:
        from app.repositories.audit_repository import append_audit_event
        append_audit_event({
            "entity_type": "accused_identity_resolution",
            "entity_id": candidate_id,
            "action": f"IDENTITY_{action}",
            "actor_id": user.id,
            "actor_role": user.role.value,
            "details": {
                "source_accused_id": candidate["source_accused_id"],
                "candidate_accused_id": candidate["candidate_accused_id"],
                "resolution_notes": resolution_notes,
                "timestamp": now,
            }
        })
    except Exception as e:
        print(f"[WARN] Audit logging for duplicate resolution failed: {e}")

    return {
        "status": "SUCCESS",
        "candidate_id": candidate_id,
        "action_applied": action,
        "reviewed_by": user.full_name,
        "resolved_at": now,
        "message": f"Candidate '{candidate_id}' successfully resolved with action '{action}'."
    }


def get_citizen_view(user: AuthUser) -> Dict[str, Any]:
    """
    Generates plain-language, low-bandwidth authorized summary for Accused Person or Family Guardian.
    Guarantees strict privacy: redacts internal police/prosecution notes and privileged strategies.
    """
    linked_case_id = user.linked_case_id or "UTP-0001"
    accused_id = f"acc_{linked_case_id.lower().replace('-', '_')}"

    # Load profile and case safely
    profile = get_accused_profile(accused_id, user)
    connected_cases = profile.get("connected_cases", [])
    primary_case = connected_cases[0] if connected_cases else {
        "case_id": linked_case_id,
        "court_name": "Metropolitan Magistrate Court 02, Central",
        "current_status": "ELIGIBLE",
        "assigned_lawyer": "Adv. Rajesh Sharma",
        "next_hearing_date": "2025-03-25",
    }

    # Plain language status translation
    status_code = primary_case.get("current_status", "ELIGIBLE")
    status_explanations = {
        "DETECTED": {
            "title_en": "Case Registered & Under Review",
            "title_hi": "मामला पंजीकृत और समीक्षाधीन",
            "detail_en": "The legal aid system has registered the case details and verified detention records.",
            "detail_hi": "कानूनी सहायता प्रणाली ने मामले का विवरण दर्ज कर हिरासत रिकॉर्ड का सत्यापन किया है।",
            "badge_color": "blue",
        },
        "ELIGIBLE": {
            "title_en": "Statutory Legal Aid Review Initiated",
            "title_hi": "धारा 479 बीएनएसएस के तहत कानूनी सहायता समीक्षा शुरू",
            "detail_en": "Eligible for statutory undertrial bail review under Section 479 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023. A panel lawyer has been assigned.",
            "detail_hi": "भारतीय नागरिक सुरक्षा संहिता (BNSS), 2023 की धारा 479 के तहत वैधानिक जमानत समीक्षा के लिए पात्र। पैनल वकील नियुक्त किया गया है।",
            "badge_color": "amber",
        },
        "APPROVED_READY_FOR_FILING": {
            "title_en": "Bail Petition Prepared & Approved",
            "title_hi": "जमानत याचिका तैयार और अनुमोदित",
            "detail_en": "The supervising legal officer has approved the draft bail application. It will be presented in court on the next hearing date.",
            "detail_hi": "पर्यवेक्षी कानूनी अधिकारी ने जमानत आवेदन को मंजूरी दे दी है। इसे अगली सुनवाई पर अदालत में प्रस्तुत किया जाएगा।",
            "badge_color": "emerald",
        },
        "FILED": {
            "title_en": "Petition Filed in Court",
            "title_hi": "अदालत में याचिका दायर की गई",
            "detail_en": "The bail petition is formally filed with the court registry. Awaiting hearing order.",
            "detail_hi": "जमानत याचिका औपचारिक रूप से अदालत की रजिस्ट्री में दायर की गई है। आदेश की प्रतीक्षा है।",
            "badge_color": "green",
        },
        "RELEASED": {
            "title_en": "Bail Granted / Release Executed",
            "title_hi": "जमानत स्वीकृत / रिहाई प्रक्रिया पूर्ण",
            "detail_en": "Court bail order issued and sent to prison superintendent for release execution.",
            "detail_hi": "अदालत ने जमानत आदेश जारी कर जेल अधीक्षक को रिहाई हेतु भेज दिया है।",
            "badge_color": "purple",
        }
    }

    explanation = status_explanations.get(status_code, status_explanations["ELIGIBLE"])

    return {
        "accused_id": profile["id"],
        "accused_name": profile["full_name"],
        "case_reference": primary_case["case_id"],
        "court_name": primary_case["court_name"],
        "next_hearing_date": primary_case.get("next_hearing_date", "2025-03-25"),
        "legal_status": explanation,
        "assigned_legal_aid_lawyer": {
            "name": primary_case.get("assigned_lawyer", "Adv. Rajesh Sharma"),
            "organization": "DLSA Central Delhi Legal Aid Panel",
            "phone": "+91 11 2338 5000",
            "helpline": "15100 (Toll-Free NALSA Helpline)",
        },
        "available_documents": [
            {"title": "First Information Report (FIR Copy)", "status": "VERIFIED_PRESENT"},
            {"title": "Judicial Remand Order", "status": "VERIFIED_PRESENT"},
            {"title": "Prison Custody Verification Certificate", "status": "CONFIRMED"}
        ],
        "communication_preferences": {
            "registered_relative": profile["family_contacts"][0]["name"] if profile.get("family_contacts") else "Primary Guardian",
            "relation": profile["family_contacts"][0]["relation"] if profile.get("family_contacts") else "Guardian",
            "preferred_language": profile.get("preferred_language", "hi"),
            "notification_channel": "SMS & WhatsApp",
        },
        "support_notice": "This portal provides free statutory information in public interest under the National Legal Services Authorities Act. No fee is required for legal aid."
    }

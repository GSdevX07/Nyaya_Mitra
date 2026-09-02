"""
domain.py - Production-Grade Normalized Domain Models for Nyaya Mitra.

Separates distinct business domains with typed models, prefixed UUIDs,
tenancy boundaries, audit traceability, and soft-deletion support.
"""

from __future__ import annotations
import uuid
import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


def generate_prefixed_id(prefix: str) -> str:
    """Generate non-sequential prefixed UUID for safe public referencing."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# ── Enumerations ─────────────────────────────────────────────────────────────

class OrganizationType(str, Enum):
    DLSA = "DLSA"
    SLSA = "SLSA"
    NALSA = "NALSA"
    PRISON_JAIL = "PRISON_JAIL"
    POLICE_STATION = "POLICE_STATION"
    REMAND_COURT = "REMAND_COURT"
    HIGH_COURT = "HIGH_COURT"
    LEGAL_AID_CLINIC = "LEGAL_AID_CLINIC"


class UserRole(str, Enum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    SLSA_SUPERVISOR = "SLSA_SUPERVISOR"
    DLSA_SECRETARY = "DLSA_SECRETARY"
    DLSA_REMAND_OFFICER = "DLSA_REMAND_OFFICER"
    JAIL_SUPERINTENDENT = "JAIL_SUPERINTENDENT"
    JAIL_INTAKE_OFFICER = "JAIL_INTAKE_OFFICER"
    LEGAL_AID_ADVOCATE = "LEGAL_AID_ADVOCATE"
    COURT_CLERK = "COURT_CLERK"
    PARALEGAL_VOLUNTEER = "PARALEGAL_VOLUNTEER"
    FAMILY_VIEWER = "FAMILY_VIEWER"


class PrisonerCategory(str, Enum):
    UNDERTRIAL = "UNDERTRIAL"
    CONVICTED = "CONVICTED"
    CIVIL_PRISONER = "CIVIL_PRISONER"
    POST_RELEASE = "POST_RELEASE"


class LegalCode(str, Enum):
    BNS_2023 = "BNS_2023"          # Bharatiya Nyaya Sanhita, 2023
    BNSS_2023 = "BNSS_2023"        # Bharatiya Nagarik Suraksha Sanhita, 2023
    IPC_1860 = "IPC_1860"          # Indian Penal Code, 1860 (Historical)
    CRPC_1973 = "CRPC_1973"        # Code of Criminal Procedure, 1973 (Historical)
    SPECIAL_LOCAL_ACTS = "SPECIAL_ACTS"


class DataSourceStatus(str, Enum):
    DEMO_SYNTHETIC = "DEMO_SYNTHETIC"
    MANUAL_INSTITUTIONAL_ENTRY = "MANUAL_INSTITUTIONAL_ENTRY"
    DOCUMENT_INGESTION = "DOCUMENT_INGESTION"
    FUTURE_GOVERNMENT_API = "FUTURE_GOVERNMENT_API"


class CaseState(str, Enum):
    INTAKE_PENDING = "INTAKE_PENDING"
    DETECTED = "DETECTED"
    LEGAL_NEED_IDENTIFIED = "LEGAL_NEED_IDENTIFIED"
    DOCUMENTS_MISSING = "DOCUMENTS_MISSING"
    DOCUMENTS_COMPLETE = "DOCUMENTS_COMPLETE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    ELIGIBLE = "ELIGIBLE"
    DRAFT_READY = "DRAFT_READY"
    LAWYER_REVIEW = "LAWYER_REVIEW"
    APPROVED_READY_FOR_FILING = "APPROVED_READY_FOR_FILING"
    FILED = "FILED"
    HEARING_SCHEDULED = "HEARING_SCHEDULED"
    ORDER_PASSED = "ORDER_PASSED"
    RELEASE_PROCESSING = "RELEASE_PROCESSING"
    RELEASED = "RELEASED"
    POST_RELEASE_PRESERVED = "POST_RELEASE_PRESERVED"
    APPEAL_PENDING = "APPEAL_PENDING"
    CLOSED = "CLOSED"


class AuditAction(str, Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    STATUS_TRANSITION = "STATUS_TRANSITION"
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    DOCUMENT_DOWNLOAD = "DOCUMENT_DOWNLOAD"
    EVIDENCE_VERIFY = "EVIDENCE_VERIFY"
    ADVOCATE_SIGN_OFF = "ADVOCATE_SIGN_OFF"
    COURT_FILING_RECORDED = "COURT_FILING_RECORDED"
    COUNSEL_ASSIGNED = "COUNSEL_ASSIGNED"
    DATA_EXPORT = "DATA_EXPORT"
    DELETE_SOFT = "DELETE_SOFT"
    SECURITY_ALERT = "SECURITY_ALERT"
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    PRIVILEGE_CHANGE = "PRIVILEGE_CHANGE"
    TOKEN_REVOCATION = "TOKEN_REVOCATION"
    INTEGRATION_ACTION = "INTEGRATION_ACTION"
    RECORD_ACCESS = "RECORD_ACCESS"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    AUDIT_LOG_VIEWED = "AUDIT_LOG_VIEWED"
    AUDIT_LOG_EXPORTED = "AUDIT_LOG_EXPORTED"
    AUDIT_RECORD_SEARCHED = "AUDIT_RECORD_SEARCHED"
    AUDIT_REPORT_GENERATED = "AUDIT_REPORT_GENERATED"
    BREAK_GLASS_ACCESS = "BREAK_GLASS_ACCESS"
    TECHNICAL_INTEGRITY_CHECK = "TECHNICAL_INTEGRITY_CHECK"


class SeverityLevel(str, Enum):
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DataStatus(str, Enum):
    REAL = "REAL"
    SYNTHETIC = "SYNTHETIC"
    MANUAL = "MANUAL"
    ESTIMATED = "ESTIMATED"
    FALLBACK = "FALLBACK"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED_AUTHENTIC = "VERIFIED_AUTHENTIC"
    TAMPERING_DETECTED = "TAMPERING_DETECTED"
    SUPERSEDED = "SUPERSEDED"


# ── Domain Entities ──────────────────────────────────────────────────────────

class Organization(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("org"))
    code: str
    name: str
    org_type: OrganizationType
    state: str
    district: str
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    deleted_at: Optional[str] = None


class Facility(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("fac"))
    organization_id: str
    name: str
    facility_type: str  # Central Jail, District Jail, Sub-Jail
    state: str
    district: str
    capacity: int = 500
    current_occupancy: int = 0
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    deleted_at: Optional[str] = None


class OrganizationUser(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("usr"))
    organization_id: str
    email: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    bar_registration_no: Optional[str] = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    deleted_at: Optional[str] = None


class TimelineItemType(str, Enum):
    FACTUAL_EVENT = "FACTUAL_EVENT"
    SYSTEM_INTERPRETATION = "SYSTEM_INTERPRETATION"


class EventCategory(str, Enum):
    CUSTODY = "CUSTODY"
    COURT_HEARING = "COURT_HEARING"
    POLICE_ACTION = "POLICE_ACTION"
    LEGAL_AID = "LEGAL_AID"
    STATUTORY_RULE = "STATUTORY_RULE"
    EVIDENCE_INTEGRITY = "EVIDENCE_INTEGRITY"
    MEDICAL_SENSITIVE = "MEDICAL_SENSITIVE"
    RELEASE_EVENT = "RELEASE_EVENT"


class VerificationStatus(str, Enum):
    VERIFIED_AUTHENTIC = "VERIFIED_AUTHENTIC"
    TAMPER_SUSPECTED = "TAMPER_SUSPECTED"
    UNVERIFIED = "UNVERIFIED"
    CONFIRMED = "CONFIRMED"
    DISPUTED = "DISPUTED"
    PENDING_REVIEW = "PENDING_REVIEW"


class CommunicationChannel(str, Enum):
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PHONE_CALL = "PHONE_CALL"
    POSTAL = "POSTAL"


class FamilyContact(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("fcon"))
    accused_id: str
    name: str
    relation: str
    phone: str
    alt_phone: Optional[str] = None
    address: Optional[str] = None
    preferred_language: str = "hi"
    preferred_channel: CommunicationChannel = CommunicationChannel.SMS
    is_primary_contact: bool = True
    verified_by_dlsa: bool = True
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class RestrictedMedicalRecord(BaseModel):
    has_vulnerability: bool = False
    vulnerability_category: Optional[str] = None  # e.g. "CHRONIC_CARDIO", "GERIATRIC", "PSYCHIATRIC", "DISABILITY"
    details_restricted: Optional[str] = None
    medical_officer_name: Optional[str] = None
    examining_facility_id: Optional[str] = None
    last_examination_date: Optional[str] = None
    treatment_underway: bool = False
    requires_hospital_referral: bool = False
    is_redacted: bool = False


class TimelineItem(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("tle"))
    accused_id: str
    case_id: Optional[str] = None
    item_type: TimelineItemType = TimelineItemType.FACTUAL_EVENT
    category: EventCategory = EventCategory.CUSTODY
    title: str
    description: str
    event_date: str
    source_name: str  # e.g. "e-Prisons Delhi", "e-Courts CIS", "CCTNS Intranet", "Nyaya Mitra BNSS Engine"
    source_record_id: Optional[str] = None
    recorded_by: str  # Official designation or system agent
    verification_status: VerificationStatus = VerificationStatus.CONFIRMED
    confidence_score: float = 1.0
    is_disputed: bool = False
    dispute_notes: Optional[str] = None
    is_sensitive_medical: bool = False
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class IdentityMatchReviewCandidate(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("imr"))
    source_accused_id: str
    source_name: str
    candidate_accused_id: str
    candidate_name: str
    match_confidence: float  # 0.0 to 1.0
    shared_traits: List[str]  # e.g. ["Exact Father Name Match", "DOB within 180 days", "Matching Facial/Biometric Hash"]
    conflicting_traits: List[str]  # e.g. ["Different Police Station of origin", "Discrepancy in recorded alias"]
    match_explanation: str
    review_status: str = "PENDING_HUMAN_REVIEW"  # PENDING_HUMAN_REVIEW, MERGED, REJECTED, ALIAS_LINKED
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class AccusedPerson(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("acc"))
    full_name: str
    alias_names: List[str] = Field(default_factory=list)
    gender: str = "Male"
    age: int = 30
    date_of_birth: Optional[str] = None
    preferred_language: str = "en"
    health_vulnerability: bool = False
    health_details: Optional[str] = None
    is_senior_citizen: bool = False
    repeat_offender: bool = False
    prior_convictions_count: int = 0
    relative_name: Optional[str] = None
    relative_relation: Optional[str] = None
    relative_phone: Optional[str] = None
    permanent_address: Optional[str] = None
    family_contacts: List[FamilyContact] = Field(default_factory=list)
    medical_record: Optional[RestrictedMedicalRecord] = None
    data_source_status: DataSourceStatus = DataSourceStatus.DEMO_SYNTHETIC
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    deleted_at: Optional[str] = None


class IdentityReference(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("idr"))
    accused_id: str
    id_type: str  # PRISON_INMATE_NO, CCTNS_PERSON_ID, VOTER_ID, AADHAAR_HASH
    id_value: str
    issuing_authority: str
    is_verified: bool = False
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class CustodyRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("cus"))
    accused_id: str
    facility_id: str
    admission_date: str
    prisoner_category: PrisonerCategory = PrisonerCategory.UNDERTRIAL
    admission_entry_no: Optional[str] = None
    calendar_custody_days: int = 0
    excluded_delay_days: int = 0
    countable_custody_days: int = 0
    is_current_custody: bool = True
    release_date: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class ArrestEvent(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("arr"))
    accused_id: str
    arrest_date: str
    arresting_police_station: str
    arresting_officer: Optional[str] = None
    first_production_date: Optional[str] = None
    first_production_court: Optional[str] = None
    remand_status: str = "JUDICIAL_REMAND"
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class FIRRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("fir"))
    fir_number: str
    police_station: str
    district: str
    state: str
    filing_date: str
    incident_date: Optional[str] = None
    summary_of_allegations: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class CourtCase(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("cas"))
    case_number: str
    accused_id: str
    fir_id: Optional[str] = None
    organization_id: str  # DLSA or Court tenant
    cnr_number: Optional[str] = None
    court_name: str
    district: str
    state: str
    legal_code: LegalCode = LegalCode.BNS_2023
    current_status: CaseState = CaseState.INTAKE_PENDING
    dlsa_reference_number: Optional[str] = None
    assigned_lawyer_id: Optional[str] = None
    assignment_status: str = "AVAILABLE"
    data_source_status: DataSourceStatus = DataSourceStatus.DEMO_SYNTHETIC
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    deleted_at: Optional[str] = None


class ChargeLegalSection(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("chg"))
    case_id: str
    legal_code: LegalCode
    section_number: str
    offence_title: str
    max_imprisonment_days: int
    is_capital_offence: bool = False
    is_life_imprisonment: bool = False
    is_bailable: bool = False
    is_compoundable: bool = False
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class CustodyCalculation(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("clc"))
    case_id: str
    rule_version: str = "BNSS_479_RULESET_V1_2023"
    calculation_timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    total_calendar_days: int
    excluded_delay_days: int
    countable_custody_days: int
    max_sentence_days: int
    statutory_threshold_fraction: str  # "1/3" or "1/2"
    threshold_days: int
    days_overdue: int
    is_eligible: bool
    requires_human_legal_review: bool = True
    review_reasons: List[str] = Field(default_factory=list)
    statutory_conditions: List[str] = Field(default_factory=list)
    disclaimer: str


class BailApplication(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("app"))
    case_id: str
    statutory_section: str = "Section 479 BNSS, 2023"
    petition_draft_text: str
    advocate_signed_off: bool = False
    signed_off_by_user_id: Optional[str] = None
    signed_off_at: Optional[str] = None
    court_filing_reference: Optional[str] = None
    filing_date: Optional[str] = None
    is_filed: bool = False
    status: str = "DRAFT"
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class DocumentRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("doc"))
    case_id: str
    document_type: str  # remand_order, charge_sheet, fir, prior_bail_order
    file_name: str
    storage_path: Optional[str] = None
    file_size_bytes: int = 0
    mime_type: str = "application/pdf"
    sha256_hash: str
    is_mandatory: bool = True
    is_present: bool = True
    uploaded_by_user_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    deleted_at: Optional[str] = None


class EvidenceItem(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("evi"))
    case_id: str
    document_id: Optional[str] = None
    document_type: str
    file_name: str
    stored_hash: str
    hash_algorithm: str = "SHA-256"
    verification_status: VerificationStatus = VerificationStatus.VERIFIED_AUTHENTIC
    last_verified_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class OCRResult(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("ocr"))
    document_id: str
    ocr_engine_used: str  # EasyOCR, PyPDF
    is_handwritten: bool = False
    confidence_score: float = 1.0
    raw_extracted_text: str
    clean_text: str
    processing_time_ms: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("aud"))
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    actor_id: str
    actor_role: str
    organization_id: Optional[str] = None
    action: AuditAction
    entity_type: str
    entity_id: str
    ip_address: Optional[str] = "127.0.0.1"
    details_json: str
    is_immutable: bool = True
    event_hash: Optional[str] = None
    previous_event_hash: Optional[str] = None
    hash_algorithm: str = "SHA-256"
    sequence_number: int = 0
    severity: str = "INFO"
    data_status: str = "REAL"

"""
schemas.py - Canonical Pydantic models for Nyaya Mitra.

Built around the Accused-Centric Persistent Dossier:
- Accused & Case Profile (Identity, FIR, Police Station, Court, DLSA)
- Independent Legal Code modeling (BNS 2023 vs IPC 1860)
- Traceable Data Provenance & Append-Oriented Case Timeline
- Two Prisoner Categories (Undertrial vs Convicted)
- Operational Legal-Needs Detection
- Post-Release Record Continuity

All case records use SYNTHETIC data only for demonstration and testing.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class PrisonerCategory(str, Enum):
    """Broad prisoner category discussed with legal counsel."""
    UNDERTRIAL = "UNDERTRIAL"
    CONVICTED = "CONVICTED"


class LegalCode(str, Enum):
    """Independent statutory criminal code context."""
    BNS_2023 = "BNS_2023"          # Bharatiya Nyaya Sanhita, 2023 (Offences post July 1, 2024)
    IPC_1860 = "IPC_1860"          # Indian Penal Code, 1860 (Historical / Transitional offences)
    SPECIAL_LOCAL_ACTS = "SPECIAL_ACTS"  # Other statutory enactments


class DataSourceStatus(str, Enum):
    """Explicit data origin status to prevent overpromising live integrations."""
    DEMO_SYNTHETIC = "DEMO_SYNTHETIC"
    MANUAL_INSTITUTIONAL_ENTRY = "MANUAL_INSTITUTIONAL_ENTRY"
    DOCUMENT_INGESTION = "DOCUMENT_INGESTION"
    FUTURE_GOVERNMENT_API = "FUTURE_GOVERNMENT_API"


class ProvenanceType(str, Enum):
    """Origin classification for every fact and document in the system."""
    MACHINE_EXTRACTED = "MACHINE_EXTRACTED"
    MACHINE_INFERRED = "MACHINE_INFERRED"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"
    HUMAN_CORRECTED = "HUMAN_CORRECTED"
    INSTITUTIONAL_ENTRY = "INSTITUTIONAL_ENTRY"
    AUTHORITATIVE_SOURCE = "AUTHORITATIVE_SOURCE"
    DEMO_SYNTHETIC = "DEMO_SYNTHETIC"
    UNKNOWN_REQUIRES_VERIFICATION = "UNKNOWN_REQUIRES_VERIFICATION"


class LegalNeedType(str, Enum):
    """Operational legal-service need identified by the system."""
    UNDERTRIAL_BAIL_479 = "UNDERTRIAL_BAIL_479"
    LEGAL_AID_COUNSEL_REQUIRED = "LEGAL_AID_COUNSEL_REQUIRED"
    MISSING_CHARGE_SHEET = "MISSING_CHARGE_SHEET"
    MISSING_REMAND_ORDER = "MISSING_REMAND_ORDER"
    MULTIPLE_PROCEEDINGS_REVIEW = "MULTIPLE_PROCEEDINGS_REVIEW"
    DELAY_ATTRIBUTION_REVIEW = "DELAY_ATTRIBUTION_REVIEW"
    MEDICAL_VULNERABILITY_REVIEW = "MEDICAL_VULNERABILITY_REVIEW"
    APPEAL_ASSISTANCE_REQUIRED = "APPEAL_ASSISTANCE_REQUIRED"
    ORDER_VERIFICATION_REQUIRED = "ORDER_VERIFICATION_REQUIRED"
    HUMAN_LEGAL_REVIEW = "HUMAN_LEGAL_REVIEW"


class MatterState(str, Enum):
    """Canonical 16-state matter lifecycle and 4 explicit exception states."""
    # Canonical Matter Lifecycle (16 States)
    INTAKE = "INTAKE"
    VERIFICATION = "VERIFICATION"
    REVIEW = "REVIEW"
    LEGAL_AID_REQUIRED = "LEGAL_AID_REQUIRED"
    ASSIGNED = "ASSIGNED"
    DOCUMENT_PENDING = "DOCUMENT_PENDING"
    ANALYSIS_READY = "ANALYSIS_READY"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    APPROVED = "APPROVED"
    SUBMITTED = "SUBMITTED"
    FILED = "FILED"
    HEARING_SCHEDULED = "HEARING_SCHEDULED"
    ORDER_RECEIVED = "ORDER_RECEIVED"
    RELEASE_WORKFLOW = "RELEASE_WORKFLOW"
    POST_RELEASE_FOLLOW_UP = "POST_RELEASE_FOLLOW_UP"
    CLOSED = "CLOSED"

    # Explicit Exception States (4 States)
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    TRANSITION_BLOCKED = "TRANSITION_BLOCKED"
    DATA_CONFLICT = "DATA_CONFLICT"
    EXTERNAL_SYNC_FAILED = "EXTERNAL_SYNC_FAILED"


class CaseState(str, Enum):
    """Procedural states across the case lifecycle with backward compatibility."""
    # Canonical States
    INTAKE = "INTAKE"
    VERIFICATION = "VERIFICATION"
    REVIEW = "REVIEW"
    LEGAL_AID_REQUIRED = "LEGAL_AID_REQUIRED"
    ASSIGNED = "ASSIGNED"
    DOCUMENT_PENDING = "DOCUMENT_PENDING"
    ANALYSIS_READY = "ANALYSIS_READY"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    APPROVED = "APPROVED"
    SUBMITTED = "SUBMITTED"
    FILED = "FILED"
    HEARING_SCHEDULED = "HEARING_SCHEDULED"
    ORDER_RECEIVED = "ORDER_RECEIVED"
    RELEASE_WORKFLOW = "RELEASE_WORKFLOW"
    POST_RELEASE_FOLLOW_UP = "POST_RELEASE_FOLLOW_UP"
    CLOSED = "CLOSED"

    # Explicit Exception States
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    TRANSITION_BLOCKED = "TRANSITION_BLOCKED"
    DATA_CONFLICT = "DATA_CONFLICT"
    EXTERNAL_SYNC_FAILED = "EXTERNAL_SYNC_FAILED"

    # Legacy Backward-Compatibility Enums
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
    ORDER_PASSED = "ORDER_PASSED"
    RELEASE_PROCESSING = "RELEASE_PROCESSING"
    RELEASED = "RELEASED"
    POST_RELEASE_PRESERVED = "POST_RELEASE_PRESERVED"
    APPEAL_PENDING = "APPEAL_PENDING"

    @classmethod
    def to_canonical(cls, state: Any) -> MatterState:
        if isinstance(state, Enum):
            val = state.value
        else:
            val = str(state)
        legacy_map = {
            "INTAKE_PENDING": MatterState.INTAKE,
            "DETECTED": MatterState.INTAKE,
            "LEGAL_NEED_IDENTIFIED": MatterState.LEGAL_AID_REQUIRED,
            "DOCUMENTS_MISSING": MatterState.DOCUMENT_PENDING,
            "DOCUMENTS_COMPLETE": MatterState.VERIFICATION,
            "MANUAL_REVIEW": MatterState.MANUAL_REVIEW_REQUIRED,
            "ELIGIBLE": MatterState.ANALYSIS_READY,
            "DRAFT_READY": MatterState.ANALYSIS_READY,
            "LAWYER_REVIEW": MatterState.HUMAN_REVIEW,
            "APPROVED_READY_FOR_FILING": MatterState.APPROVED,
            "ORDER_PASSED": MatterState.ORDER_RECEIVED,
            "RELEASE_PROCESSING": MatterState.RELEASE_WORKFLOW,
            "RELEASED": MatterState.RELEASE_WORKFLOW,
            "POST_RELEASE_PRESERVED": MatterState.POST_RELEASE_FOLLOW_UP,
            "APPEAL_PENDING": MatterState.HUMAN_REVIEW,
        }
        if val in legacy_map:
            return legacy_map[val]
        try:
            return MatterState(val)
        except ValueError:
            return MatterState.MANUAL_REVIEW_REQUIRED


class UrgencyFlags(BaseModel):
    """Operational urgency metadata used to prioritize human review queues."""
    age: int = Field(..., description="Age of the accused person in years.", ge=0)
    health_flag: bool = Field(
        default=False,
        description="True if documented health condition exists. Contextual trigger for human review; not an autonomous medical bail decision.",
    )
    health_details: Optional[str] = Field(
        default=None,
        description="Contextual medical notes for human legal officer review.",
    )
    repeat_offender: bool = Field(
        default=False,
        description="True if prior convictions exist (determines 1/3 vs 1/2 detention fraction under Section 479).",
    )


class TimelineEvent(BaseModel):
    """Chronological event in the accused person's legal journey."""
    id: str = Field(..., description="Unique event identifier, e.g. 'TLE-001'.")
    timestamp: str = Field(..., description="ISO 8601 datetime of the event.")
    event_type: str = Field(..., description="Category: INTAKE, CUSTODY, DOCUMENT, ELIGIBILITY, ADVOCATE, DRAFT, FILING, HEARING, ORDER, RELEASE, WORKFLOW, APPROVAL, HANDOFF, EXCEPTION.")
    title: str = Field(..., description="Concise human-readable title.")
    description: str = Field(..., description="Detailed description of what occurred.")
    actor: str = Field(default="System", description="Name of person or service who performed or confirmed the action.")
    actor_role: str = Field(default="Automated Pipeline", description="Institutional role: Jail Officer, DLSA Secretary, Legal Officer, Court Clerk, System.")
    source: str = Field(default="System", description="Data origin: Remand Sheet, Jail Register, OCR Pipeline, Manual Entry, AI, External Sync.")
    is_human_verified: bool = Field(default=False, description="True if a human officer confirmed this event.")
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    artifact_id: Optional[str] = None
    artifact_version_id: Optional[str] = None
    decision: Optional[str] = None
    comment: Optional[str] = None
    provenance_badge: Optional[str] = None  # USER, SYSTEM, AI, EXTERNAL_SYNC


class DataProvenance(BaseModel):
    """Field-level evidentiary provenance record."""
    field_name: str
    provenance_type: ProvenanceType
    source_document_id: Optional[str] = None
    entered_or_verified_by: Optional[str] = None
    timestamp: Optional[str] = None
    confidence_score: Optional[float] = None
    notes: Optional[str] = None


class AppealMetadata(BaseModel):
    """Metadata for convicted prisoners seeking appellate assistance."""
    conviction_date: str = Field(..., description="Date judgment of conviction was pronounced (YYYY-MM-DD).")
    trial_court_name: str = Field(..., description="Name of the convicting trial court, e.g. 'Sessions Court, Saket'.")
    sentence_awarded_days: int = Field(..., description="Total sentence of imprisonment awarded in days.")
    appellate_forum: str = Field(default="High Court of Judicature", description="Appropriate appellate forum.")
    judgment_document_available: bool = Field(default=False, description="True if certified copy of judgment is on record.")
    limitation_status: str = Field(
        default="Requires legal verification by counsel",
        description="Appeal limitation disclaimer; exact computation requires certified copy exclusion calculation.",
    )
    appeal_preparation_status: str = Field(
        default="Pending Document Retrieval",
        description="Current stage of appellate legal aid.",
    )


class PostReleaseDetails(BaseModel):
    """Preserved legal continuity details after release."""
    release_date: str = Field(..., description="Date of release from custody (YYYY-MM-DD).")
    release_order_reference: str = Field(..., description="Court bail/release order number.")
    surety_type: str = Field(default="Personal Bond with One Surety", description="Bond terms specified by court.")
    preservation_status: str = Field(
        default="Dossier Preserved for Post-Release Continuity",
        description="Status of preserved legal case records under retention rules.",
    )
    follow_up_notes: Optional[str] = Field(
        default=None,
        description="Notes for subsequent counsel or trial tracking.",
    )


class LegalNeedItem(BaseModel):
    """Structured legal assistance need identified for a case."""
    need_type: LegalNeedType
    title: str
    description: str
    urgency: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, URGENT")
    blocking_bail_workflow: bool = Field(default=False, description="True if missing doc or review blocks petition filing.")
    status: str = Field(default="ACTION_REQUIRED", description="ACTION_REQUIRED, IN_PROGRESS, RESOLVED")


class CaseRecord(BaseModel):
    """
    Canonical Persistent Accused Dossier.
    Represents the full legal journey of an accused or convicted person.
    """
    # Core Identifiers
    case_id: str = Field(..., description="Unique case dossier ID, e.g. 'UTP-0007' or 'CONV-0101'.")
    name: str = Field(..., description="Name of the person. Must contain '(Synthetic)' in all demo data.")
    prisoner_category: PrisonerCategory = Field(default=PrisonerCategory.UNDERTRIAL)
    legal_code: LegalCode = Field(default=LegalCode.BNS_2023)
    offense_sections: List[str] = Field(..., description="List of charged statutory sections, e.g. ['BNS 303(2)'].")
    
    # Procedural & Institutional Identifiers
    cnr_number: Optional[str] = Field(default=None, description="16-character eCourts Case Number Record (CNR) identifier.")
    fir_number: Optional[str] = Field(default=None, description="FIR Number, e.g. 'FIR-2024-089'.")
    police_station: Optional[str] = Field(default=None, description="Police station having jurisdiction.")
    police_station_id: Optional[str] = Field(default=None, description="Station identifier, e.g. 'ps_kotwali_central'.")
    court_name: Optional[str] = Field(default=None, description="Jurisdictional court, e.g. 'Chief Judicial Magistrate, Central'.")
    district: Optional[str] = Field(default=None, description="District, e.g. 'South Delhi'.")
    state: Optional[str] = Field(default="Delhi", description="State / UT, e.g. 'Delhi'.")
    dlsa_reference_number: Optional[str] = Field(default=None, description="DLSA Legal Aid Reference Number, e.g. 'DLSA-SD-2024-419'.")

    # Custody & Statutory Metrics
    arrest_date: str = Field(..., description="Date of arrest in ISO 8601 format (YYYY-MM-DD).")
    custody_days: int = Field(..., description="Total elapsed calendar days spent in custody.", ge=0)
    excluded_delay_days: int = Field(default=0, description="Detention days excluded due to delay attributable to the accused.", ge=0)
    max_sentence_days_for_offense: int = Field(..., description="Maximum statutory sentence for the most serious charged offence.", ge=0)
    punishable_by_death_or_life: bool = Field(default=False, description="True if offence is punishable by death or life imprisonment (Section 479 exclusion).")
    multiple_active_cases: bool = Field(default=False, description="True if investigation/trial in more than one offence or multiple cases is pending.")

    # Status & Workflow State
    status: CaseState = Field(default=CaseState.DETECTED)
    data_source_status: DataSourceStatus = Field(default=DataSourceStatus.DEMO_SYNTHETIC)
    prior_bail_orders: List[str] = Field(default_factory=list)
    
    # Document Inventory
    required_docs: List[str] = Field(default_factory=lambda: ["remand_order", "charge_sheet"])
    present_docs: List[str] = Field(default_factory=list)

    # Operational Urgency & Location
    urgency_flags: UrgencyFlags = Field(...)
    jail_location: str = Field(..., description="Detention facility name, e.g. 'Central Jail No. 4, Tihar (Synthetic)'.")
    preferred_language: str = Field(default="en", description="BCP-47 / ISO 639-1 language code, e.g. 'hi', 'ta', 'en'.")

    # Authorised Family Contact (Privacy-controlled)
    relative_name: Optional[str] = Field(default="Not Specified")
    relative_relation: Optional[str] = Field(default="Parent/Relative")
    relative_phone: Optional[str] = Field(default="+91 98765 43210")
    permanent_address: Optional[str] = Field(default="Synthetic Address, District Detention Zone")

    # Legal Aid Assignment Workflow
    assignment_status: str = Field(default="AVAILABLE", description="'AVAILABLE', 'ASSIGNED', or 'DECLINED'.")
    assigned_lawyer_id: Optional[str] = Field(default=None)
    assigned_lawyer: Optional[str] = Field(default=None, description="Name or title of assigned legal aid counsel.")

    # Rich Dossier Sub-Models
    legal_needs: List[LegalNeedItem] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    data_provenance: Dict[str, Any] = Field(default_factory=dict)
    appeal_details: Optional[AppealMetadata] = Field(default=None)
    post_release_details: Optional[PostReleaseDetails] = Field(default=None)


class LawyerProfile(BaseModel):
    """Institutional profile for DLSA panel advocate / legal officer."""
    id: str = Field(..., description="Advocate / Legal Officer ID, e.g. 'Legal Officer 104'.")
    full_name: str = Field(..., description="Full legal name of the advocate.")
    bar_association_id: str = Field(..., description="State Bar Association Registration Number.")
    email: str = Field(..., description="Official contact email.")
    phone: str = Field(..., description="Official mobile number.")
    specialization: str = Field(..., description="Practice area / panel specialization.")
    organization: str = Field(default="District Legal Services Authority (DLSA)")
    cases_taken: int = Field(default=0)
    status: str = Field(default="Active Pro Bono Counsel")


class PlatformActionRequest(BaseModel):
    action_type: str = Field(..., description="Action to execute, e.g. 'CONNECTOR_RETRY'.")
    target: Optional[str] = Field(default=None, description="Optional target resource or service.")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Optional parameters for action execution.")


class DocumentCorrectionRequest(BaseModel):
    field_name: str = Field(..., description="Name of the extracted field, e.g. 'custody_days', 'legal_sections'.")
    corrected_value: Any = Field(..., description="Corrected value provided by authorized reviewer.")
    correction_reason: str = Field(..., description="Justification and explanation for the correction.")
    version_id: Optional[str] = Field(default=None, description="Optional version ID to link the correction to.")


class ReprocessDocumentRequest(BaseModel):
    reason: Optional[str] = Field(default="Reprocessing requested for updated extraction", description="Reason for reprocessing.")
    custom_text_override: Optional[str] = Field(default=None, description="Optional revised text content.")


# ── Stage 9: Matter Lifecycle, Approvals & Handoff Schemas ─────────────────────

class MatterTransitionRequest(BaseModel):
    """Named workflow transition request with payload and optimistic locking."""
    transition: str = Field(..., description="Named transition action, e.g. 'START_VERIFICATION', 'APPROVE_MATTER', 'RECORD_FILING'.")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Optional contextual payload (hearing_date, filing_ref, etc.).")
    comment: Optional[str] = Field(default=None, description="Optional rationale or institutional notes.")
    expected_version: Optional[int] = Field(default=None, description="Expected matter version number for concurrency/optimistic locking.")


class MatterApprovalRequest(BaseModel):
    """First-class formal approval or decision on an exact artifact version."""
    artifact_id: str = Field(..., description="ID of the artifact being approved (e.g. 'art_bail_draft_01').")
    artifact_version_id: str = Field(..., description="Exact artifact version ID (e.g. 'ver_bail_draft_v1').")
    artifact_type: str = Field(default="BAIL_APPLICATION", description="Artifact classification (BAIL_APPLICATION, CASE_SUMMARY, LEGAL_ANALYSIS, FILING_PACKAGE).")
    decision: str = Field(..., description="'APPROVED', 'REJECTED', or 'CHANGES_REQUESTED'.")
    comment: Optional[str] = Field(default=None, description="Review commentary or reasoning.")
    approval_level: int = Field(default=1, description="1 for Primary/Advocate sign-off, 2 for Supervisory Legal Officer sign-off.")


class MatterHandoffRequest(BaseModel):
    """Immutable case reassignment and handoff packet."""
    to_user_id: str = Field(..., description="ID of the incoming assignee.")
    to_role: str = Field(..., description="Role of the incoming assignee.")
    reason: str = Field(..., description="Detailed institutional reason for handoff/reassignment.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata or handover instructions.")


class MatterArtifactCreateRequest(BaseModel):
    """Register or version an immutable legal artifact."""
    artifact_id: str = Field(..., description="Unique artifact grouping identifier.")
    artifact_type: str = Field(..., description="Artifact category, e.g. 'BAIL_APPLICATION', 'CASE_SUMMARY'.")
    content_text: str = Field(..., description="Full text or serialized content of the artifact.")
    is_ai_generated: bool = Field(default=False, description="True if generated by AI model. Sets provenance to AI_ASSISTED.")
    ai_model_name: Optional[str] = Field(default=None, description="AI model identity if AI-generated.")
    version_tag: Optional[str] = Field(default=None, description="Optional semantic version tag, e.g. 'bail_draft_v1'.")


class ExternalSyncRequest(BaseModel):
    """Externally synchronized court or prison registry payload."""
    source_system: str = Field(..., description="External authority or system, e.g. 'eCourts_Portal', 'ICJS_Sync'.")
    external_reference: str = Field(..., description="External case or proceeding reference number.")
    received_data: Dict[str, Any] = Field(..., description="Synchronized data attributes.")
    sync_result: str = Field(default="SUCCESS", description="Outcome status of the sync operation.")


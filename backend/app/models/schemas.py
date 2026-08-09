"""
Pydantic models / data schemas for Nyaya Mitra.

All case records in the system use SYNTHETIC data only.
No real prisoner names or personal records are referenced anywhere.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class CaseState(str, Enum):
    """Lifecycle states of a bail application case."""
    DETECTED = "DETECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    ELIGIBLE = "ELIGIBLE"
    DOCUMENTS_MISSING = "DOCUMENTS_MISSING"
    DOCUMENTS_COMPLETE = "DOCUMENTS_COMPLETE"
    DRAFT_READY = "DRAFT_READY"
    LAWYER_REVIEW = "LAWYER_REVIEW"
    APPROVED = "APPROVED"
    FILED = "FILED"
    HEARING_SCHEDULED = "HEARING_SCHEDULED"
    ORDER_PASSED = "ORDER_PASSED"
    RELEASED = "RELEASED"
    CLOSED = "CLOSED"


class UrgencyFlags(BaseModel):
    """Urgency metadata used by the Prioritization Agent to rank cases."""

    age: int = Field(
        ...,
        description="Age of the undertrial prisoner in years.",
        ge=0,
    )
    health_flag: bool = Field(
        ...,
        description="True if the prisoner has a documented serious health condition.",
    )
    repeat_offender: bool = Field(
        ...,
        description="True if the prisoner has prior convictions or pending cases.",
    )


class CaseRecord(BaseModel):
    """
    Canonical data model for one undertrial prisoner case.

    IMPORTANT: Every record in this system uses synthetic data
    generated for development and demonstration purposes only.
    The 'name' field must always contain the marker string
    'synthetic - not a real person' to make this explicit.
    """

    case_id: str = Field(
        ...,
        description="Unique identifier for this case, e.g. 'UTP-0007'.",
        examples=["UTP-0001"],
    )
    name: str = Field(
        ...,
        description=(
            "Name of the prisoner — MUST be marked as "
            "'synthetic - not a real person' in all mock data."
        ),
        examples=["synthetic - not a real person"],
    )
    offense_sections: List[str] = Field(
        ...,
        description="List of IPC/BNS sections charged, e.g. ['IPC 379', 'IPC 411'].",
        examples=[["IPC 379"]],
    )
    arrest_date: str = Field(
        ...,
        description="Date of arrest in ISO 8601 format (YYYY-MM-DD).",
        examples=["2024-11-02"],
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    custody_days: int = Field(
        ...,
        description="Total number of days spent in custody as of today.",
        ge=0,
    )
    max_sentence_days_for_offense: int = Field(
        ...,
        description=(
            "Maximum sentence (in days) prescribed for the most serious "
            "offense in offense_sections. Used by the Eligibility Agent "
            "to compute the Section 479 BNSS threshold (half the max term)."
        ),
        ge=0,
    )
    punishable_by_death_or_life: bool = Field(
        default=False,
        description="True if the offense is punishable by death or life imprisonment (excluded from Sec 479).",
    )
    multiple_active_cases: bool = Field(
        default=False,
        description="True if the prisoner is facing trial in more than one active case / multiple FIRs.",
    )
    status: CaseState = Field(
        default=CaseState.DETECTED,
        description="Current workflow status of the case.",
    )
    prior_bail_orders: List[str] = Field(
        default_factory=list,
        description=(
            "List of prior bail order references, if any. "
            "Empty list means first bail application."
        ),
    )
    required_docs: List[str] = Field(
        ...,
        description=(
            "Documents legally required to proceed with the bail application, "
            "e.g. ['remand_order', 'charge_sheet', 'prior_bail_order_if_any']."
        ),
    )
    present_docs: List[str] = Field(
        ...,
        description=(
            "Documents that are currently available / on record. "
            "The Completeness Agent diffs this against required_docs."
        ),
    )
    urgency_flags: UrgencyFlags = Field(
        ...,
        description=(
            "Structured urgency metadata consumed by the Prioritization Agent "
            "to compute a weighted urgency score."
        ),
    )
    jail_location: str = Field(
        ...,
        description="Name of the jail / detention facility. Synthetic value for mock data.",
        examples=["District Jail, synthetic"],
    )
    preferred_language: str = Field(
        ...,
        description=(
            "BCP-47 / ISO 639-1 language code for the prisoner's preferred language. "
            "Used by the Multilingual Explainer Agent, e.g. 'hi' for Hindi."
        ),
        examples=["hi", "ta", "en"],
    )
    relative_name: str = Field(
        default="Not Specified",
        description="Full name of accused prisoner's parent, spouse, or guardian.",
    )
    relative_relation: str = Field(
        default="Parent/Relative",
        description="Relationship of contact person to the undertrial prisoner.",
    )
    relative_phone: str = Field(
        default="+91 98765 43210",
        description="Contact phone number of parent or relative.",
    )
    permanent_address: str = Field(
        default="Synthetic Address, District Detention Zone",
        description="Permanent home address of accused prisoner or family.",
    )
    assignment_status: str = Field(
        default="AVAILABLE",
        description="Status of case assignment: 'AVAILABLE', 'ASSIGNED', or 'DECLINED'.",
    )
    assigned_lawyer_id: Optional[str] = Field(
        default=None,
        description="ID of lawyer assigned to take up the case.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "UTP-0007",
                "name": "synthetic - not a real person",
                "offense_sections": ["IPC 379"],
                "arrest_date": "2024-11-02",
                "custody_days": 410,
                "max_sentence_days_for_offense": 730,
                "prior_bail_orders": [],
                "required_docs": [
                    "remand_order",
                    "charge_sheet",
                    "prior_bail_order_if_any",
                ],
                "present_docs": ["remand_order", "charge_sheet"],
                "urgency_flags": {
                    "age": 63,
                    "health_flag": True,
                    "repeat_offender": False,
                },
                "punishable_by_death_or_life": False,
                "multiple_active_cases": False,
                "status": "DETECTED",
                "jail_location": "District Jail, synthetic",
                "preferred_language": "hi",
                "relative_name": "Sunita Devi (Wife)",
                "relative_relation": "Spouse",
                "relative_phone": "+91 98765 77007",
                "permanent_address": "Flat 12B, Old City Suburb, Jaipur, RJ - 302001",
                "assignment_status": "AVAILABLE",
                "assigned_lawyer_id": None,
            }
        }
    }


class LawyerProfile(BaseModel):
    """Profile model for active lawyer/legal officer."""

    id: str = Field(..., description="Unique Lawyer ID, e.g. 'Legal Officer 104'.")
    full_name: str = Field(..., description="Full legal name of the advocate.")
    bar_association_id: str = Field(..., description="State Bar Association Registration ID.")
    email: str = Field(..., description="Primary email address.")
    phone: str = Field(..., description="Contact mobile number.")
    specialization: str = Field(..., description="Legal practice specialization.")
    cases_taken: int = Field(default=0, description="Total cases currently assigned/taken.")
    status: str = Field(default="Active", description="Lawyer account status.")


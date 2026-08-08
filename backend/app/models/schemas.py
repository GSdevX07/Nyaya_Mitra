"""
Pydantic models / data schemas for Nyaya Mitra.

All case records in the system use SYNTHETIC data only.
No real prisoner names or personal records are referenced anywhere.
"""

from pydantic import BaseModel, Field
from typing import List


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
                "jail_location": "District Jail, synthetic",
                "preferred_language": "hi",
            }
        }
    }

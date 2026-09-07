"""
app/models/tasks.py — Authoritative Operational Task Queue Schemas & Authority Workflows.
========================================================================================
Defines schemas for the Universal Task Queue engine, safe bulk actions, custody intake,
custody events, inmate profile completion, and prison release confirmation.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class TaskPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskStatus(str, Enum):
    NEW = "NEW"
    PENDING_ACTION = "PENDING_ACTION"
    WAITING_FOR_DOCUMENTS = "WAITING_FOR_DOCUMENTS"
    UNDER_REVIEW = "UNDER_REVIEW"
    OVERDUE = "OVERDUE"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"
    EXCEPTION = "EXCEPTION"


class TaskQueueItem(BaseModel):
    id: str
    case_id: str
    accused_name: str = "Under-Trial Accused"
    task_type: str
    title: str
    description: Optional[str] = None
    owner_role: str
    owner_user_id: Optional[str] = None
    owner_name: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: str
    source: str
    reason: str
    status: TaskStatus = TaskStatus.NEW
    escalation_path: str
    facility: Optional[str] = "Designated Correctional Facility"
    district: Optional[str] = "Competent District"
    custody_duration_days: int = 0
    document_completeness_pct: int = 100
    has_data_conflict: bool = False
    legal_aid_need: bool = False
    assignment_status: str = "AVAILABLE"
    matter_status: str = "INTAKE"
    hearing_date: Optional[str] = None
    is_consequential: bool = False
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    completed_by: Optional[str] = None


class TaskUpdateRequest(BaseModel):
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    owner_user_id: Optional[str] = None
    owner_name: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None


class BulkTaskActionRequest(BaseModel):
    action: str = Field(..., description="Action name: ASSIGN_OWNER, MARK_REVIEWED, UPDATE_METADATA, ACKNOWLEDGE")
    task_ids: List[str] = Field(..., min_length=1, description="List of target task IDs")
    owner_user_id: Optional[str] = None
    owner_name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[TaskStatus] = None


class CustodyIntakeRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Full name of admitted accused/inmate")
    inmate_number: Optional[str] = Field(None, description="Prison admission / UTP registration number")
    facility_id: str = Field(..., description="Target correctional facility ID")
    facility_name: Optional[str] = Field(None, description="Correctional facility name")
    district: str = Field(..., description="Judicial district jurisdiction")
    court_name: Optional[str] = Field("Competent Court", description="Producing or remand court")
    offense_sections: List[str] = Field(default_factory=lambda: ["IPC 379 / BNS 303"], description="Sections charged")
    arrest_date: str = Field(..., description="Date of formal arrest (YYYY-MM-DD)")
    admission_date: Optional[str] = Field(None, description="Date admitted to prison (YYYY-MM-DD)")
    max_sentence_days: Optional[int] = Field(1095, description="Maximum sentence in days for primary charge")
    refer_to_dlsa: bool = Field(True, description="Immediately flag legal aid requirement for DLSA panel assignment")
    notes: Optional[str] = Field(None, description="Intake observation notes")


class CustodyEventRequest(BaseModel):
    event_type: str = Field(..., description="REMAND_EXTENSION, COURT_PRODUCTION, FACILITY_TRANSFER, MEDICAL_REVIEW, DISCIPLINARY")
    event_date: str = Field(..., description="Date event occurred (YYYY-MM-DD)")
    court_name: Optional[str] = Field(None, description="Relevant court or destination")
    notes: str = Field(..., min_length=3, description="Official remarks / escort log")
    verified: bool = Field(True, description="Officer verification status")


class AccusedProfileUpdateRequest(BaseModel):
    father_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    permanent_address: Optional[str] = None
    contact_number: Optional[str] = None
    emergency_family_contact_name: Optional[str] = None
    emergency_family_contact_phone: Optional[str] = None
    emergency_family_contact_relation: Optional[str] = None
    identification_marks: Optional[str] = None


class PrisonReleaseConfirmationRequest(BaseModel):
    release_date: str = Field(..., description="Date and time of physical custody release")
    gate_pass_number: str = Field(..., min_length=2, description="Official prison gate-pass / discharge memo number")
    surety_verification_ref: Optional[str] = Field(None, description="Court release order / solvent surety verification reference")
    superintendent_notes: Optional[str] = Field(None, description="Discharge log remarks")


class ExpediteCoordinationRequest(BaseModel):
    notes: Optional[str] = Field("Expediting missing charge sheet / custody certificate.", description="Institutional coordination directives")
    target_roles: Optional[List[str]] = Field(default_factory=lambda: ["JAIL_OFFICER", "POLICE_OFFICER"], description="Agencies / roles to alert")

"""
models/citizen.py — Pydantic Schemas for Accused and Family Experience.
=====================================================================
Constrained, mobile-first models for plain-language legal aid access,
citizen action requests, notification preferences, and entitled documents.
"""
from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CitizenRequestType(str, Enum):
    REQUEST_HELP = "REQUEST_HELP"
    FLAG_INCORRECT_INFO = "FLAG_INCORRECT_INFO"
    REQUEST_DOCUMENT_COPY = "REQUEST_DOCUMENT_COPY"
    REQUEST_DLSA_CONTACT = "REQUEST_DLSA_CONTACT"


class CitizenRequestStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    ACTION_TAKEN = "ACTION_TAKEN"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CitizenActionRequestCreate(BaseModel):
    request_type: CitizenRequestType
    subject: str = Field(..., min_length=3, max_length=200)
    details: str = Field(..., min_length=5, max_length=2000)
    target_document_type: Optional[str] = None
    discrepancy_field: Optional[str] = None


class CitizenNotificationPreferencesUpdate(BaseModel):
    phone_number: Optional[str] = None
    channel_sms_enabled: bool = True
    channel_whatsapp_enabled: bool = True
    channel_in_app_enabled: bool = True
    preferred_language: str = "en"
    consent_status: str = "OPTED_IN"
    consent_text: Optional[str] = None


class CitizenDocumentSummaryItem(BaseModel):
    id: str
    document_type: str
    title: str
    status: str
    uploaded_at: Optional[str] = None
    file_size_bytes: int = 0
    file_size_formatted: str = ""
    text_summary: str
    is_approved_for_citizen: bool = True


class CitizenMissingDocumentItem(BaseModel):
    document_type: str
    title: str
    why_needed: str
    how_to_submit: str
    urgency: str  # REQUIRED_BEFORE_HEARING, OPTIONAL_SUPPORTING


class CitizenUpcomingEventItem(BaseModel):
    event_type: str
    title: str
    event_date: str
    court_or_location: str
    instructions: str


class CitizenAiExplanation(BaseModel):
    is_ai_generated: bool = True
    disclaimer_type: str = "PROCEDURAL_EXPLANATION_NOT_JUDICIAL_DECISION"
    disclaimer_label: str = "AI Procedural Explanation — Not a Legal Decision"
    disclaimer_text: str = (
        "This explanation is provided in plain language to help you understand your current case status. "
        "It is NOT a court order, legal judgment, or guarantee. Bail and release determinations rest solely "
        "with the competent Court of Law under judicial discretion. Nyaya Mitra never promises release outcomes."
    )
    explanation_text: str
    derived_language: str
    is_derived_display: bool = False
    authoritative_english_text: str


class CitizenOverviewResponse(BaseModel):
    portal_mode: str  # ACCUSED_USER or FAMILY_GUARDIAN
    accused_id: str
    accused_name: str
    case_reference: str
    court_name: str
    police_station: str
    current_known_status: Dict[str, Any]
    filing_details: Dict[str, Any]
    release_details: Dict[str, Any]
    upcoming_known_events: List[CitizenUpcomingEventItem]
    legal_aid_support: Dict[str, Any]
    missing_documents_from_citizen: List[CitizenMissingDocumentItem]
    approved_entitled_documents: List[CitizenDocumentSummaryItem]
    ai_procedural_explanation: CitizenAiExplanation
    language_meta: Dict[str, Any]
    notification_preferences: Dict[str, Any]
    recent_citizen_requests: List[Dict[str, Any]]
    low_bandwidth_mode_supported: bool = True
    support_helpline: str = "15100"
    support_notice: str

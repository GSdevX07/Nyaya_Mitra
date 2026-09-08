"""
routes/accused_routes.py — REST API Routes for Accused-Centric Profiles,
Timeline (Facts vs System Interpretations), Identity Resolution, and Citizen Portal.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, require_role
from app.auth.user_store import AuthUser
from app.auth.roles import Role
from app.services.accused_service import (
    get_accused_profile,
    get_accused_timeline,
    get_duplicate_candidates,
    resolve_duplicate_candidate,
    update_accused_identity_attributes,
    get_citizen_view,
)
from app.models.citizen import (
    CitizenActionRequestCreate,
    CitizenNotificationPreferencesUpdate,
)
from app.services.language_service import get_supported_languages
from app.services.citizen_service import (
    get_citizen_overview,
    get_citizen_entitled_documents,
    get_citizen_document_summary,
    submit_citizen_action_request,
    get_citizen_action_requests_for_user,
    get_notification_preferences_service,
    update_notification_preferences_service,
)


accused_router = APIRouter(prefix="/accused", tags=["Accused-Centric Profile & Timeline"])
citizen_router = APIRouter(prefix="/citizen", tags=["Citizen & Family Assistance"])


class DuplicateResolutionRequest(BaseModel):
    candidate_id: str
    action: str  # MERGE_RECORDS, REJECT_MATCH, MARK_AS_ALIAS
    resolution_notes: str


class UpdateAccusedIdentityRequest(BaseModel):
    full_name: Optional[str] = None
    aliases: Optional[List[str]] = None
    father_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    government_identifiers: Optional[Dict[str, Any]] = None
    update_reason: str


# ── Accused-Centric Profile Endpoints ─────────────────────────────────────────

@accused_router.get("/duplicates/candidates", response_model=List[Dict[str, Any]])
async def list_duplicate_candidates(
    status: Optional[str] = Query("PENDING_HUMAN_REVIEW"),
    current_user: AuthUser = Depends(require_role(
        Role.DLSA_OFFICER, Role.SUPERVISING_LEGAL_OFFICER, Role.GOV_ADMIN, Role.PLATFORM_ADMIN,
    )),
):
    """
    Retrieve candidate duplicate identities detected across facilities/records
    for human-in-the-loop legal review.
    """
    return get_duplicate_candidates(current_user, status_filter=status)


@accused_router.patch("/{accused_id}/identity", response_model=Dict[str, Any])
async def update_identity(
    accused_id: str,
    body: UpdateAccusedIdentityRequest,
    current_user: AuthUser = Depends(require_role(Role.SUPERVISING_LEGAL_OFFICER)),
):
    """
    Update consolidated legal identity attributes for an accused person.
    Strictly authorized to SUPERVISING_LEGAL_OFFICER.
    """
    if not body.update_reason or len(body.update_reason.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A substantive statutory reason (minimum 5 characters) is required to update identity records.",
        )
    return update_accused_identity_attributes(
        accused_id=accused_id,
        attributes=body.model_dump(exclude_unset=True),
        actor=current_user,
    )


@accused_router.post("/duplicates/resolve")
async def resolve_duplicate(
    body: DuplicateResolutionRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Execute human-in-the-loop duplicate resolution (MERGE, REJECT, or ALIAS).
    Requires supervising legal officer or administrator role.
    """
    return resolve_duplicate_candidate(
        candidate_id=body.candidate_id,
        action=body.action,
        resolution_notes=body.resolution_notes,
        user=current_user,
    )


@accused_router.get("/{accused_id}", response_model=Dict[str, Any])
async def get_profile(
    accused_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Get consolidated accused person profile across multiple cases and facilities.
    Applies strict ABAC medical quarantining and privacy controls.
    """
    return get_accused_profile(accused_id=accused_id, user=current_user)


@accused_router.get("/{accused_id}/timeline", response_model=List[Dict[str, Any]])
async def get_timeline(
    accused_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Get chronological timeline separating factual events from system-generated interpretations.
    Indicates source provenance, recording authority, and verification status for every item.
    """
    return get_accused_timeline(accused_id=accused_id, user=current_user)


@accused_router.get("/{accused_id}/cases", response_model=List[Dict[str, Any]])
async def get_cases(
    accused_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Get all court cases linked to this individual across all detention facilities.
    """
    profile = get_accused_profile(accused_id=accused_id, user=current_user)
    return profile.get("connected_cases", [])


# ── Citizen / Family Portal Endpoints ─────────────────────────────────────────

@citizen_router.get("/my-case", response_model=Dict[str, Any])
async def get_my_case_citizen_view(
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Get simplified, plain-language legal aid status for the logged-in Accused Person or Family Guardian.
    Zero internal police or prosecution notes exposed.
    """
    return get_citizen_view(user=current_user)


@citizen_router.get("/timeline", response_model=List[Dict[str, Any]])
async def get_my_case_citizen_timeline(
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Get citizen-safe chronological milestone timeline for the logged-in citizen's linked case.
    Filters out internal audit events, security boundary logs, and raw system calculations.
    """
    if not current_user.linked_case_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active legal aid case is linked to your account.",
        )
    from app.services.accused_service import get_citizen_timeline
    return get_citizen_timeline(case_id=current_user.linked_case_id, user=current_user)


# ── Stage 11: Constrained Mobile-First Citizen Endpoints ─────────────────────

@citizen_router.get("/overview", response_model=Dict[str, Any])
async def get_overview(
    lang: str = Query("en", description="Target display language (en, hi, kn, te, ta, mr, bn)"),
    current_user: AuthUser = Depends(require_role(Role.ACCUSED_USER, Role.FAMILY_GUARDIAN)),
):
    """
    Consolidated, mobile-first, low-bandwidth dashboard for Accused Person or Family Guardian.
    Includes case references, known status, upcoming events, counsel assignment,
    missing citizen documents, approved entitled copies, and AI explanation with statutory disclaimer.
    """
    return get_citizen_overview(user=current_user, lang=lang)


@citizen_router.get("/languages", response_model=List[Dict[str, Any]])
async def list_supported_languages(
    current_user: AuthUser = Depends(get_current_user),
):
    """
    List configured Indian languages and authoritative status.
    """
    return get_supported_languages()


@citizen_router.get("/documents", response_model=List[Dict[str, Any]])
async def list_entitled_documents(
    lang: str = Query("en"),
    current_user: AuthUser = Depends(require_role(Role.ACCUSED_USER, Role.FAMILY_GUARDIAN)),
):
    """
    List approved documents that the citizen is entitled to receive,
    with plain-language text summaries for low-bandwidth environments.
    """
    if not current_user.linked_case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active linked case.")
    return get_citizen_entitled_documents(current_user.linked_case_id, lang=lang)


@citizen_router.get("/documents/{doc_id}/summary", response_model=Dict[str, Any])
async def get_doc_summary(
    doc_id: str,
    lang: str = Query("en"),
    current_user: AuthUser = Depends(require_role(Role.ACCUSED_USER, Role.FAMILY_GUARDIAN)),
):
    """
    Retrieve plain-text preview and dynamic summary of an entitled document for low-bandwidth mode.
    """
    if not current_user.linked_case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active linked case.")
    return get_citizen_document_summary(doc_id, current_user.linked_case_id, lang=lang)


@citizen_router.post("/requests", response_model=Dict[str, Any])
async def create_request(
    body: CitizenActionRequestCreate,
    current_user: AuthUser = Depends(require_role(Role.ACCUSED_USER, Role.FAMILY_GUARDIAN)),
):
    """
    Submit a structured citizen action request (Help, Discrepancy Flag, Copy Request, DLSA Contact).
    Directly dispatches an operational task to the DLSA Task Queue.
    """
    return submit_citizen_action_request(user=current_user, payload=body)


@citizen_router.get("/requests", response_model=List[Dict[str, Any]])
async def list_requests(
    current_user: AuthUser = Depends(require_role(Role.ACCUSED_USER, Role.FAMILY_GUARDIAN)),
):
    """
    List past citizen requests and their DLSA review status.
    """
    return get_citizen_action_requests_for_user(user=current_user)


@citizen_router.get("/notification-preferences", response_model=Dict[str, Any])
async def get_notification_preferences(
    current_user: AuthUser = Depends(require_role(Role.ACCUSED_USER, Role.FAMILY_GUARDIAN)),
):
    """
    Retrieve active notification preferences, channel settings, and statutory consent record.
    """
    return get_notification_preferences_service(user=current_user)


@citizen_router.post("/notification-preferences", response_model=Dict[str, Any])
async def update_notification_preferences(
    body: CitizenNotificationPreferencesUpdate,
    request: Request,
    current_user: AuthUser = Depends(require_role(Role.ACCUSED_USER, Role.FAMILY_GUARDIAN)),
):
    """
    Update channel opt-ins (SMS, WhatsApp, In-App) and record statutory consent.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return update_notification_preferences_service(user=current_user, payload=body, ip_address=client_ip)


# ── Privacy Notice & Consent Workflows ──────────────────────────────────────

class ConsentSubmissionRequest(BaseModel):
    consent_type: str = "DATA_PROCESSING"
    version: str = "2026.1"


class ConsentRevocationRequest(BaseModel):
    consent_type: str = "DATA_PROCESSING"
    reason: str = "USER_REQUEST"


@citizen_router.get("/privacy-notice")
async def fetch_privacy_notice(lang: str = Query("en")):
    """
    Plain-language multi-lingual legal privacy notice explaining purpose,
    categories of data processed, who has access, and statutory rights.
    """
    from app.security.consent import get_privacy_notice
    return get_privacy_notice(language=lang)


@citizen_router.post("/consent")
async def grant_privacy_consent(
    body: ConsentSubmissionRequest,
    request: Request,
    current_user: AuthUser = Depends(require_role(Role.ACCUSED_USER, Role.FAMILY_GUARDIAN)),
):
    """
    Record affirmative, informed consent from an accused person or family member.
    """
    from app.security.consent import record_consent
    from app.database import get_db_connection

    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")
    conn = get_db_connection()
    try:
        res = record_consent(
            conn=conn,
            citizen_id=current_user.id,
            consent_type=body.consent_type,
            version=body.version,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return res
    finally:
        conn.close()


@citizen_router.post("/consent/revoke")
async def revoke_privacy_consent(
    body: ConsentRevocationRequest,
    request: Request,
    current_user: AuthUser = Depends(require_role(Role.ACCUSED_USER, Role.FAMILY_GUARDIAN)),
):
    """
    Revoke previously granted consent.
    """
    from app.security.consent import revoke_consent
    from app.database import get_db_connection

    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")
    conn = get_db_connection()
    try:
        res = revoke_consent(
            conn=conn,
            citizen_id=current_user.id,
            consent_type=body.consent_type,
            reason=body.reason,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return res
    finally:
        conn.close()


@citizen_router.get("/consent/status")
async def check_consent_status(
    consent_type: str = Query("DATA_PROCESSING"),
    current_user: AuthUser = Depends(require_role(Role.ACCUSED_USER, Role.FAMILY_GUARDIAN)),
):
    """
    Check active consent status for authenticated citizen.
    """
    from app.security.consent import get_consent_status
    from app.database import get_db_connection

    conn = get_db_connection()
    try:
        return get_consent_status(conn=conn, citizen_id=current_user.id, consent_type=consent_type)
    finally:
        conn.close()



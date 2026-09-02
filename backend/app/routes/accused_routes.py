"""
routes/accused_routes.py — REST API Routes for Accused-Centric Profiles,
Timeline (Facts vs System Interpretations), Identity Resolution, and Citizen Portal.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.auth.user_store import AuthUser
from app.auth.roles import Role
from app.services.accused_service import (
    get_accused_profile,
    get_accused_timeline,
    get_duplicate_candidates,
    resolve_duplicate_candidate,
    get_citizen_view,
)


accused_router = APIRouter(prefix="/accused", tags=["Accused-Centric Profile & Timeline"])
citizen_router = APIRouter(prefix="/citizen", tags=["Citizen & Family Assistance"])


class DuplicateResolutionRequest(BaseModel):
    candidate_id: str
    action: str  # MERGE_RECORDS, REJECT_MATCH, MARK_AS_ALIAS
    resolution_notes: str


# ── Accused-Centric Profile Endpoints ─────────────────────────────────────────

@accused_router.get("/duplicates/candidates", response_model=List[Dict[str, Any]])
async def list_duplicate_candidates(
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Retrieve candidate duplicate identities detected across facilities/records
    for human-in-the-loop legal review.
    """
    return get_duplicate_candidates(current_user)


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

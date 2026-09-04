"""
app.workflow.routes - Server-Enforced Matter/Case Lifecycle REST API.
====================================================================
Exposes authoritative endpoints for transitions, approvals, artifacts, handoffs,
timeline inspection, and external synchronization.
All actions enforce strict Nyaya Mitra role ownership.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.auth.dependencies import get_current_user, AuthUser
from app.auth.roles import Role
from app.models.schemas import (
    MatterTransitionRequest,
    MatterApprovalRequest,
    MatterHandoffRequest,
    MatterArtifactCreateRequest,
    ExternalSyncRequest,
    MatterState,
)
from app.workflow.service import WorkflowService, ConcurrencyConflictError
from app.workflow.state_machine import WorkflowStateMachine
from app.database import get_matter_approvals, get_matter_artifact_versions, get_active_matter_artifact

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Workflow & Matter Lifecycle"])


@router.post("/matters/{case_id}/transitions")
@router.post("/cases/{case_id}/transitions")
async def execute_transition_endpoint(
    case_id: str,
    req: MatterTransitionRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Authoritative state transition request.
    Validates state machine rules, actor roles, required evidence, and concurrency.
    """
    try:
        result = WorkflowService.execute_transition(
            case_id=case_id,
            action=req.transition,
            actor=current_user,
            payload=req.payload,
            comment=req.comment,
            expected_version=req.expected_version,
            is_ai_agent=False,
        )
        return result
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected transition failure: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Workflow transition failed.")


@router.get("/matters/{case_id}/state")
@router.get("/cases/{case_id}/state")
async def get_case_state_endpoint(
    case_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve current authoritative lifecycle state, version, and case metadata."""
    try:
        canonical_state, version_number, case_data = WorkflowService.get_case_state(case_id)
        return {
            "case_id": case_id,
            "canonical_state": canonical_state.value,
            "raw_status": case_data.get("status") or case_data.get("current_status"),
            "version_number": version_number,
            "assigned_advocate_id": case_data.get("assigned_advocate_id"),
            "assigned_advocate_name": case_data.get("assigned_advocate_name"),
            "filing_reference": case_data.get("filing_reference"),
            "hearing_date": case_data.get("hearing_date"),
        }
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/matters/{case_id}/available-transitions")
@router.get("/cases/{case_id}/available-transitions")
async def get_available_transitions_endpoint(
    case_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """List valid transitions from the current state and indicate if the calling user can execute each."""
    try:
        canonical_state, version_number, _ = WorkflowService.get_case_state(case_id)
        transitions = WorkflowStateMachine.get_available_transitions(
            current_state=canonical_state,
            actor_role=current_user.role,
        )
        return {
            "case_id": case_id,
            "current_state": canonical_state.value,
            "version_number": version_number,
            "available_transitions": transitions,
        }
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/matters/{case_id}/approvals")
@router.post("/cases/{case_id}/approvals")
async def record_approval_endpoint(
    case_id: str,
    req: MatterApprovalRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Record first-class institutional approval decision for an exact artifact version."""
    try:
        result = WorkflowService.record_approval(
            case_id=case_id,
            artifact_id=req.artifact_id,
            artifact_version_id=req.artifact_version_id,
            artifact_type=req.artifact_type,
            decision=req.decision,
            comment=req.comment,
            actor=current_user,
            approval_level=req.approval_level,
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/matters/{case_id}/approvals")
@router.get("/cases/{case_id}/approvals")
async def get_matter_approvals_endpoint(
    case_id: str,
    artifact_version_id: Optional[str] = Query(None),
    current_user: AuthUser = Depends(get_current_user),
):
    """List approvals recorded for a matter or specific artifact version."""
    approvals = get_matter_approvals(case_id, artifact_version_id)
    return {"case_id": case_id, "approvals": approvals}


@router.post("/matters/{case_id}/artifacts")
@router.post("/cases/{case_id}/artifacts")
async def create_artifact_endpoint(
    case_id: str,
    req: MatterArtifactCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Create an immutable artifact version N+1 with SHA-256 hash."""
    try:
        result = WorkflowService.create_artifact_version(
            case_id=case_id,
            artifact_id=req.artifact_id,
            artifact_type=req.artifact_type,
            content_text=req.content_text,
            actor=current_user,
            is_ai_generated=req.is_ai_generated,
            ai_model_name=req.ai_model_name,
            version_tag=req.version_tag,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/matters/{case_id}/artifacts")
@router.get("/cases/{case_id}/artifacts")
async def list_artifacts_endpoint(
    case_id: str,
    artifact_id: Optional[str] = Query(None),
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve versions of legal artifacts registered for the matter."""
    versions = get_matter_artifact_versions(case_id, artifact_id)
    active = get_active_matter_artifact(case_id, "BAIL_APPLICATION")
    return {
        "case_id": case_id,
        "artifact_versions": versions,
        "active_artifact": active,
    }


@router.post("/matters/{case_id}/handoff")
@router.post("/cases/{case_id}/handoff")
async def execute_handoff_endpoint(
    case_id: str,
    req: MatterHandoffRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Reassign case and record immutable handoff packet."""
    try:
        result = WorkflowService.record_handoff(
            case_id=case_id,
            to_user_id=req.to_user_id,
            to_role=req.to_role,
            reason=req.reason,
            actor=current_user,
            metadata=req.metadata,
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/matters/{case_id}/handoff-summary")
@router.get("/cases/{case_id}/handoff-summary")
async def get_handoff_summary_endpoint(
    case_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve comprehensive handoff packet for incoming counsel."""
    try:
        summary = WorkflowService.get_handoff_summary(case_id)
        return summary
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/matters/{case_id}/timeline")
async def get_matter_timeline_endpoint(
    case_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve unified chronological timeline with provenance badges (USER, SYSTEM, AI, EXTERNAL_SYNC)."""
    events = WorkflowService.get_matter_timeline(case_id)
    return {"case_id": case_id, "timeline": events}


@router.post("/matters/{case_id}/external-sync")
@router.post("/cases/{case_id}/external-sync")
async def record_external_sync_endpoint(
    case_id: str,
    req: ExternalSyncRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Record external court or prison registry sync."""
    result = WorkflowService.record_external_sync(
        case_id=case_id,
        source_system=req.source_system,
        external_reference=req.external_reference,
        received_data=req.received_data,
        actor=current_user,
    )
    return result

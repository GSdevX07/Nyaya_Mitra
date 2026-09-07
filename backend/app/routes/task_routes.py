"""
app/routes/task_routes.py — Universal Operational Task Queue & Authority Operations REST API.
=============================================================================================
Exposes endpoints for the task queue, safe bulk actions, custody intake, custody events,
accused profile updates, and physical release confirmation.
Strictly validates institutional roles and authority boundaries server-side.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.auth.dependencies import get_current_user, require_role, AuthUser
from app.auth.roles import Role
from app.models.tasks import (
    TaskQueueItem,
    TaskUpdateRequest,
    BulkTaskActionRequest,
    CustodyIntakeRequest,
    CustodyEventRequest,
    AccusedProfileUpdateRequest,
    PrisonReleaseConfirmationRequest,
    ExpediteCoordinationRequest,
)
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authority Task Queue & Operations"])


# ── 1. Operational Task Queue ────────────────────────────────────────────────

@router.get("/tasks/queue", response_model=List[Dict[str, Any]])
async def get_operational_task_queue_endpoint(
    facility: Optional[str] = Query(None, description="Filter by correctional facility or police station"),
    district: Optional[str] = Query(None, description="Filter by judicial district"),
    priority: Optional[str] = Query(None, description="Filter by priority: CRITICAL, HIGH, MEDIUM, LOW"),
    custody_duration_min: Optional[int] = Query(None, description="Minimum days spent in custody"),
    document_completeness_max: Optional[int] = Query(None, description="Maximum document completeness percentage"),
    legal_aid_need: Optional[bool] = Query(None, description="Filter by legal aid requirement flag"),
    hearing_date_from: Optional[str] = Query(None, description="Hearing date from (YYYY-MM-DD)"),
    hearing_date_to: Optional[str] = Query(None, description="Hearing date to (YYYY-MM-DD)"),
    has_data_conflict: Optional[bool] = Query(None, description="Filter by unresolved data conflict exception"),
    assignment_status: Optional[str] = Query(None, description="Filter by assignment status (e.g. AVAILABLE, ASSIGNED)"),
    matter_status: Optional[str] = Query(None, description="Filter by canonical matter state"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    search: Optional[str] = Query(None, description="Search across title, reason, accused name, case ID"),
    sort_by: Optional[str] = Query("due_date", description="Sort by: due_date, priority, custody_duration_days, created_at, status"),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc, desc"),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Retrieve authoritative, role-scoped operational task queue items.
    Enforces strict role boundaries:
    - Jail Officers: Facility-scoped custody tasks
    - DLSA Officers: District-scoped legal-aid intake, panel assignment, and document tasks
    - Supervising Legal Officers: Supervisory review, draft verification, and exception tasks
    - Defense Advocates: Strictly tasks for cases assigned to the advocate
    - Police Users: Scoped exclusively to assigned station records
    """
    try:
        tasks = TaskService.get_task_queue(
            current_user=current_user,
            facility=facility,
            district=district,
            priority=priority,
            custody_duration_min=custody_duration_min,
            document_completeness_max=document_completeness_max,
            legal_aid_need=legal_aid_need,
            hearing_date_from=hearing_date_from,
            hearing_date_to=hearing_date_to,
            has_data_conflict=has_data_conflict,
            assignment_status=assignment_status,
            matter_status=matter_status,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return tasks
    except Exception as e:
        logger.error(f"Failed to retrieve operational task queue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve task queue.")


@router.patch("/tasks/{task_id}")
async def update_operational_task_endpoint(
    task_id: str,
    req: TaskUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Update task status, priority, or owner for safe administrative progression.
    Blocks generic mutation of legally consequential tasks.
    """
    try:
        updates = req.model_dump(exclude_unset=True)
        result = TaskService.update_task(task_id, updates, current_user)
        return result
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/tasks/bulk-action")
async def execute_bulk_task_action_endpoint(
    req: BulkTaskActionRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Execute safe, reversible bulk actions on multiple task queue items.
    STRICT SERVER-SIDE GUARD: Rejects any attempt to perform consequential actions
    (approvals, filings, releases, closures) in bulk with HTTP 400.
    """
    try:
        payload = req.model_dump(exclude_unset=True)
        result = TaskService.execute_bulk_action(req.action, req.task_ids, payload, current_user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ── 2. Jail Officer Specific Workflows ────────────────────────────────────────

@router.post("/cases/intake-custody", tags=["Jail Operations"])
@router.post("/jail/intake-inmate", tags=["Jail Operations"])
async def intake_custody_record_endpoint(
    req: CustodyIntakeRequest,
    current_user: AuthUser = Depends(require_role(Role.JAIL_OFFICER, Role.PLATFORM_ADMIN)),
):
    """
    Intake a newly admitted undertrial prisoner into institutional prison custody.
    Creates records in accused_persons, custody_records, cases, and triggers initial tasks.
    Strictly scoped to officer's assigned correctional facility.
    """
    try:
        result = TaskService.intake_new_custody_record(req, current_user)
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/cases/{case_id}/custody-events", tags=["Jail Operations"])
@router.post("/jail/{case_id}/custody-events", tags=["Jail Operations"])
async def record_custody_event_endpoint(
    case_id: str,
    req: CustodyEventRequest,
    current_user: AuthUser = Depends(require_role(Role.JAIL_OFFICER, Role.PLATFORM_ADMIN)),
):
    """
    Record verified prison custody event (remand extension, transfer, court production).
    Appends immutable verified entry to case chronological timeline.
    """
    try:
        result = TaskService.record_custody_event(case_id, req, current_user)
        return result
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/cases/{case_id}/accused-profile", tags=["Accused Profile"])
@router.patch("/accused/{case_id}/profile", tags=["Accused Profile"])
async def update_accused_profile_endpoint(
    case_id: str,
    req: AccusedProfileUpdateRequest,
    current_user: AuthUser = Depends(require_role(Role.JAIL_OFFICER, Role.DLSA_OFFICER, Role.PLATFORM_ADMIN)),
):
    """
    Capture missing accused/inmate profile information (guardian, DOB, address, contact).
    Preserves institutional provenance and updates accused dossier.
    """
    try:
        result = TaskService.update_accused_profile(case_id, req, current_user)
        return result
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/cases/{case_id}/confirm-release", tags=["Jail Operations"])
@router.post("/jail/{case_id}/confirm-release", tags=["Jail Operations"])
async def confirm_prison_release_endpoint(
    case_id: str,
    req: PrisonReleaseConfirmationRequest,
    current_user: AuthUser = Depends(require_role(Role.JAIL_OFFICER)),
):
    """
    Confirm physical discharge of inmate from prison custody upon court bail grant.
    Strictly restricted to JAIL_OFFICER.
    Executes authoritative state transition to POST_RELEASE_FOLLOW_UP.
    """
    try:
        result = TaskService.confirm_prison_release(case_id, req, current_user)
        return result
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/cases/{case_id}/expedite-coordination", tags=["DLSA Operations"])
async def expedite_document_coordination_endpoint(
    case_id: str,
    req: Optional[ExpediteCoordinationRequest] = None,
    current_user: AuthUser = Depends(require_role(
        Role.DLSA_OFFICER, Role.SUPERVISING_LEGAL_OFFICER, Role.PLATFORM_ADMIN
    )),
):
    """
    Dispatch institutional document coordination notice to Police and Jail authorities.
    Creates an operational task in the universal task queue, appends a case timeline event,
    and sends targeted real-time alerts to Jail and Police officers.
    """
    try:
        notes = req.notes if req else "Expediting missing charge sheet / custody certificate."
        target_roles = req.target_roles if req else ["JAIL_OFFICER", "POLICE_OFFICER"]
        result = TaskService.dispatch_document_coordination(
            case_id=case_id,
            notes=notes,
            current_user=current_user,
            target_roles=target_roles,
        )
        return result
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


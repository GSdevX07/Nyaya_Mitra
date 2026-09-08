"""
app.routes.notification_routes — Production Notification and Escalation Endpoints.
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, require_role, AuthUser
from app.auth.roles import Role
from app.notifications.schemas import (
    NotificationEventType,
    NotificationChannel,
    NotificationPriority,
    NotificationRecord,
    UserNotificationPreferences,
    NotificationFilter,
    EscalationPolicy,
)
from app.notifications.service import NotificationService
from app.notifications.repository import NotificationRepository
from app.notifications.escalation import EscalationManager

logger = logging.getLogger("nyaya_mitra.api.notifications")

router = APIRouter(prefix="/notifications", tags=["Notification Engine"])


class DispatchEventRequest(BaseModel):
    event_type: NotificationEventType
    payload: Dict[str, Any] = {}
    case_id: Optional[str] = None
    recipient: Optional[str] = None
    target_role: Optional[str] = None
    user_id: Optional[str] = None
    priority: Optional[NotificationPriority] = None
    channels: Optional[List[NotificationChannel]] = None
    org_id: str = "DEFAULT"


class UpdatePreferencesRequest(BaseModel):
    preferred_language: Optional[str] = "en"
    enabled_channels: Optional[List[NotificationChannel]] = None
    quiet_hours_enabled: Optional[bool] = False
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "06:00"
    phone_number: Optional[str] = None
    email: Optional[str] = None


class DeliveryWebhookPayload(BaseModel):
    external_message_id: str
    status: str
    error: Optional[str] = None


@router.get("", response_model=List[NotificationRecord])
def list_notifications_endpoint(
    is_read: Optional[bool] = None,
    is_acknowledged: Optional[bool] = None,
    priority: Optional[NotificationPriority] = None,
    event_type: Optional[NotificationEventType] = None,
    channel: Optional[NotificationChannel] = None,
    case_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    include_dismissed: bool = False,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Retrieve filterable notifications matching user role and jurisdiction.
    Soft-dismissed notifications are excluded by default unless include_dismissed=True.
    Supports date range filtering (date_from, date_to).
    """
    filters = NotificationFilter(
        is_read=is_read,
        is_acknowledged=is_acknowledged,
        priority=priority,
        event_type=event_type,
        channel=channel,
        case_id=case_id,
        date_from=date_from,
        date_to=date_to,
        include_dismissed=include_dismissed,
    )
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    return NotificationRepository.get_notifications_filtered(
        user_id=current_user.id,
        role=role_val,
        linked_case_id=current_user.linked_case_id,
        filters=filters,
    )


@router.patch("/{notif_id}/acknowledge")
def acknowledge_notification_endpoint(
    notif_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Acknowledge a notification with strict recipient/role authorization check.
    Preserves full audit trail and marks record acknowledged by user with read_at timestamp.
    """
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    success, reason = NotificationService.acknowledge_with_status(notif_id, current_user.id, role=role_val)
    if not success:
        if reason == "FORBIDDEN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You are not authorized to acknowledge this notification.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notif_id} not found.",
        )
    return {"status": "success", "id": notif_id, "acknowledged_by": current_user.id}


@router.post("/{notif_id}/dismiss")
def dismiss_notification_endpoint(
    notif_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Soft-dismiss a notification from user view with authorization check.
    Does NOT delete the record from database or audit ledger.
    """
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    success, reason = NotificationService.dismiss_with_status(notif_id, current_user.id, role=role_val)
    if not success:
        if reason == "FORBIDDEN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You are not authorized to dismiss this notification.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notif_id} not found.",
        )
    return {
        "status": "success",
        "id": notif_id,
        "message": "Notification dismissed from view. Audit record preserved.",
    }


@router.patch("/{notif_id}/read")
def mark_notification_read_endpoint(
    notif_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Mark a single notification as read and record read_at timestamp.
    """
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    success, reason = NotificationService.mark_read_with_status(notif_id, current_user.id, role=role_val)
    if not success:
        if reason == "FORBIDDEN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You are not authorized to mark this notification as read.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notif_id} not found.",
        )
    return {"status": "success", "id": notif_id, "is_read": True}


@router.post("/mark-all-read")
def mark_all_read_endpoint(
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Mark all unread notifications visible to the current user as read.
    """
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    count = NotificationService.mark_all_read(current_user.id, role=role_val)
    return {"status": "success", "marked_read_count": count}


@router.post("/escalations/process")
def trigger_escalations_endpoint(
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER
    )),
):
    """
    Trigger immediate scan and execution of pending automatic escalations.
    """
    from app.notifications.scheduler import process_pending_escalations
    escalated = process_pending_escalations()
    return {
        "status": "success",
        "escalated_count": len(escalated),
        "escalated_ids": [r.id for r in escalated],
    }


@router.post("/webhook/{channel}")
def delivery_webhook_endpoint(
    channel: NotificationChannel,
    payload: DeliveryWebhookPayload,
):
    """
    Public webhook receiver for SMS/Email/WhatsApp delivery status updates (SENT -> DELIVERED / FAILED).
    """
    updated = NotificationService.handle_delivery_webhook(
        channel=channel,
        external_message_id=payload.external_message_id,
        event_status=payload.status,
        error_message=payload.error,
    )
    return {"status": "success", "updated": updated}


@router.post("/dispatch", response_model=NotificationRecord)
def dispatch_notification_endpoint(
    req: DispatchEventRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Dispatches an event notification through the governed notification engine.
    Applies idempotency check, quiet-hours rules, and adapter execution.
    """
    return NotificationService.dispatch(
        event_type=req.event_type,
        payload=req.payload,
        case_id=req.case_id,
        recipient=req.recipient,
        target_role=req.target_role,
        user_id=req.user_id,
        priority=req.priority,
        channels=req.channels,
        org_id=req.org_id,
    )


@router.post("/{notif_id}/escalate", response_model=Optional[NotificationRecord])
def escalate_notification_endpoint(
    notif_id: str,
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER
    )),
):
    """
    Manually or programmatically triggers next-tier escalation for an unresolved notification.
    """
    escalated = NotificationService.escalate(notif_id)
    if not escalated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Notification {notif_id} could not be escalated further.",
        )
    return escalated


@router.get("/preferences", response_model=UserNotificationPreferences)
def get_preferences_endpoint(
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve personal notification delivery preferences and quiet hours."""
    return NotificationRepository.get_user_preferences(current_user.id)


@router.put("/preferences", response_model=UserNotificationPreferences)
def update_preferences_endpoint(
    req: UpdatePreferencesRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Update personal delivery channels, language preference, and quiet hours."""
    existing = NotificationRepository.get_user_preferences(current_user.id)
    updated = UserNotificationPreferences(
        user_id=current_user.id,
        preferred_language=req.preferred_language or existing.preferred_language,
        enabled_channels=req.enabled_channels if req.enabled_channels is not None else existing.enabled_channels,
        quiet_hours_enabled=req.quiet_hours_enabled if req.quiet_hours_enabled is not None else existing.quiet_hours_enabled,
        quiet_hours_start=req.quiet_hours_start or existing.quiet_hours_start,
        quiet_hours_end=req.quiet_hours_end or existing.quiet_hours_end,
        phone_number=req.phone_number or existing.phone_number,
        email=req.email or existing.email,
    )
    NotificationRepository.save_user_preferences(updated)
    return updated


@router.get("/escalation-policies")
def list_escalation_policies_endpoint(
    org_id: str = "DEFAULT",
    current_user: AuthUser = Depends(get_current_user),
):
    """View configurable escalation policies for organization events."""
    policies = {}
    for ev in NotificationEventType:
        policies[ev.value] = EscalationManager.get_policy(org_id, ev)
    return policies


@router.put("/escalation-policies")
def update_escalation_policy_endpoint(
    policy: EscalationPolicy,
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.SUPERVISING_LEGAL_OFFICER
    )),
):
    """Configure multi-tier escalation chain for an organization event."""
    EscalationManager.save_policy(policy)
    return {"status": "success", "policy_id": policy.id}


@router.get("/dlq")
def get_dlq_endpoint(
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN
    )),
):
    """List Dead-Letter Queue items for delivery monitoring and remediation."""
    return NotificationRepository.get_dlq_entries()


@router.post("/dlq/{dlq_id}/retry")
def retry_dlq_endpoint(
    dlq_id: str,
    current_user: AuthUser = Depends(require_role(
        Role.PLATFORM_ADMIN, Role.GOV_ADMIN
    )),
):
    """Manually re-dispatch a failed notification in the dead-letter queue."""
    success = NotificationService.retry_dlq(dlq_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to retry DLQ item {dlq_id}.",
        )
    return {"status": "success", "message": f"DLQ item {dlq_id} successfully reprocessed."}

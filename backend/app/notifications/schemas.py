"""
app.notifications.schemas — Canonical Schemas & Enums for Nyaya Mitra Notifications.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class NotificationEventType(str, Enum):
    NEW_LEGAL_AID_NEED = "NEW_LEGAL_AID_NEED"
    APPROACHING_CUSTODY_THRESHOLD = "APPROACHING_CUSTODY_THRESHOLD"
    OVERDUE_ACTION = "OVERDUE_ACTION"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    HEARING_APPROACHING = "HEARING_APPROACHING"
    ORDER_RECEIVED = "ORDER_RECEIVED"
    RELEASE_RECORDED = "RELEASE_RECORDED"
    UNRESOLVED_IDENTITY_CONFLICT = "UNRESOLVED_IDENTITY_CONFLICT"
    INTEGRATION_FAILURE = "INTEGRATION_FAILURE"
    SECURITY_EVENT = "SECURITY_EVENT"


class NotificationChannel(str, Enum):
    IN_APP = "IN_APP"
    SMS = "SMS"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"


class NotificationPriority(str, Enum):
    LOW = "LOW"
    STANDARD = "STANDARD"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class RetryAttempt(BaseModel):
    attempt_number: int
    timestamp: str
    channel: NotificationChannel
    error_message: Optional[str] = None
    success: bool = False


class ChannelDeliveryResult(BaseModel):
    success: bool
    channel: NotificationChannel
    external_message_id: Optional[str] = None
    error: Optional[str] = None
    retryable: bool = True


class NotificationRecord(BaseModel):
    id: str
    recipient: str = Field(description="User ID, target role, or contact address")
    target_role: Optional[str] = "ALL"
    user_id: Optional[str] = None
    case_id: Optional[str] = None
    channel: NotificationChannel = NotificationChannel.IN_APP
    event_type: NotificationEventType
    priority: NotificationPriority = NotificationPriority.STANDARD
    title: str
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    retry_history: List[RetryAttempt] = Field(default_factory=list)
    idempotency_key: str
    organization_id: str = "DEFAULT"
    escalation_tier: int = 1
    is_read: bool = False
    read_at: Optional[str] = None
    is_acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    is_dismissed: bool = False
    dismissed_at: Optional[str] = None


class UserNotificationPreferences(BaseModel):
    user_id: str
    preferred_language: str = "en"
    enabled_channels: List[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.IN_APP, NotificationChannel.EMAIL]
    )
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "06:00"
    phone_number: Optional[str] = None
    email: Optional[str] = None


class EscalationTierConfig(BaseModel):
    tier: int
    target_role: str
    wait_minutes: int
    channels: List[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.IN_APP]
    )


class EscalationPolicy(BaseModel):
    id: str
    org_id: str
    event_type: NotificationEventType
    tiers: List[EscalationTierConfig] = Field(default_factory=list)
    updated_at: Optional[str] = None


class NotificationFilter(BaseModel):
    is_read: Optional[bool] = None
    is_acknowledged: Optional[bool] = None
    priority: Optional[NotificationPriority] = None
    event_type: Optional[NotificationEventType] = None
    channel: Optional[NotificationChannel] = None
    case_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    include_dismissed: bool = False

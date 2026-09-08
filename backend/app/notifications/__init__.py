"""
app.notifications — Production Notification and Escalation Subsystem for Nyaya Mitra.
"""
from app.notifications.schemas import (
    NotificationEventType,
    NotificationChannel,
    NotificationPriority,
    DeliveryStatus,
    RetryAttempt,
    NotificationRecord,
    UserNotificationPreferences,
    EscalationTierConfig,
    EscalationPolicy,
    ChannelDeliveryResult,
    NotificationFilter,
)
from app.notifications.service import NotificationService
from app.notifications.repository import NotificationRepository
from app.notifications.rules import compute_idempotency_key, format_event_content, EVENT_RULE_REGISTRY
from app.notifications.preferences import is_in_quiet_hours, can_bypass_quiet_hours, filter_channels_for_delivery
from app.notifications.escalation import EscalationManager

__all__ = [
    "NotificationEventType",
    "NotificationChannel",
    "NotificationPriority",
    "DeliveryStatus",
    "RetryAttempt",
    "NotificationRecord",
    "UserNotificationPreferences",
    "EscalationTierConfig",
    "EscalationPolicy",
    "ChannelDeliveryResult",
    "NotificationFilter",
    "NotificationService",
    "NotificationRepository",
    "compute_idempotency_key",
    "format_event_content",
    "EVENT_RULE_REGISTRY",
    "is_in_quiet_hours",
    "can_bypass_quiet_hours",
    "filter_channels_for_delivery",
    "EscalationManager",
]

"""
app.notifications.preferences — User Notification Preferences, Quiet Hours & Emergency Overrides.
"""
from __future__ import annotations

import datetime
import logging
from typing import Optional, Dict, Any, Tuple
from app.notifications.schemas import (
    NotificationPriority,
    NotificationEventType,
    UserNotificationPreferences,
    NotificationChannel,
)

logger = logging.getLogger("nyaya_mitra.notifications.preferences")

EMERGENCY_OVERRIDE_EVENTS = {
    NotificationEventType.SECURITY_EVENT,
    NotificationEventType.APPROACHING_CUSTODY_THRESHOLD,
    NotificationEventType.UNRESOLVED_IDENTITY_CONFLICT,
    NotificationEventType.RELEASE_RECORDED,
}


def is_in_quiet_hours(
    now: Optional[datetime.datetime] = None,
    prefs: Optional[UserNotificationPreferences] = None,
) -> bool:
    """
    Evaluates whether the given time falls inside the user's configured quiet hours window.
    Correctly handles overnight windows (e.g., 22:00 -> 06:00).
    """
    if not prefs or not prefs.quiet_hours_enabled:
        return False

    current_time = (now or datetime.datetime.now(datetime.timezone.utc)).time()

    try:
        start_h, start_m = map(int, prefs.quiet_hours_start.split(":"))
        end_h, end_m = map(int, prefs.quiet_hours_end.split(":"))
        start_t = datetime.time(start_h, start_m)
        end_t = datetime.time(end_h, end_m)

        if start_t <= end_t:
            # Daytime window, e.g. 13:00 -> 15:00
            return start_t <= current_time <= end_t
        else:
            # Overnight window, e.g. 22:00 -> 06:00
            return current_time >= start_t or current_time <= end_t
    except Exception as e:
        logger.warning(f"Error parsing quiet hours '{prefs.quiet_hours_start}'-'{prefs.quiet_hours_end}': {e}")
        return False


def can_bypass_quiet_hours(
    priority: NotificationPriority,
    event_type: NotificationEventType,
) -> bool:
    """
    Statutory & Safety Override:
    Emergency notifications, security events, approaching custody thresholds,
    and inmate identity conflicts strictly bypass quiet hours.
    """
    if priority == NotificationPriority.EMERGENCY:
        return True
    if event_type in EMERGENCY_OVERRIDE_EVENTS:
        return True
    return False


def filter_channels_for_delivery(
    priority: NotificationPriority,
    event_type: NotificationEventType,
    prefs: UserNotificationPreferences,
    requested_channels: Optional[list[NotificationChannel]] = None,
    now: Optional[datetime.datetime] = None,
) -> Tuple[list[NotificationChannel], bool]:
    """
    Determines active delivery channels considering quiet hours and emergency overrides.
    Even if explicit requested_channels are supplied, quiet hours are strictly evaluated,
    and disruptive channels (SMS, WhatsApp) are filtered out unless the event qualifies
    for statutory or safety emergency bypass.
    Returns (allowed_channels, is_emergency_override).
    """
    in_quiet = is_in_quiet_hours(now, prefs)
    emergency_override = can_bypass_quiet_hours(priority, event_type)

    base_channels = list(requested_channels) if requested_channels else list(prefs.enabled_channels)
    if not base_channels:
        base_channels = [NotificationChannel.IN_APP]

    if in_quiet and not emergency_override:
        # Suppress disruptive channels (SMS, WhatsApp)
        # Allow IN_APP silently for user inbox
        suppressed_channels = [
            ch for ch in base_channels if ch == NotificationChannel.IN_APP
        ]
        if not suppressed_channels:
            suppressed_channels = [NotificationChannel.IN_APP]
        logger.info(
            f"Quiet hours active: suppressed external alerts for user {prefs.user_id} "
            f"(channels filtered from {[c.value for c in base_channels]} to {[c.value for c in suppressed_channels]})"
        )
        return suppressed_channels, False

    # Normal delivery or emergency override:
    active_channels = list(base_channels)
    if emergency_override and NotificationChannel.SMS not in active_channels:
        active_channels.append(NotificationChannel.SMS)

    return active_channels, emergency_override

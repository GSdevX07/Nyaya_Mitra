"""
app.notifications.escalation — Multi-Tier Escalation Chains Configurable per Organization.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from app.notifications.schemas import (
    NotificationEventType,
    NotificationChannel,
    EscalationTierConfig,
    EscalationPolicy,
)

logger = logging.getLogger("nyaya_mitra.notifications.escalation")

# In-memory store fallback for organization policies
_ESCALATION_POLICIES: Dict[str, EscalationPolicy] = {}


def get_default_escalation_policy(
    org_id: str,
    event_type: NotificationEventType,
) -> EscalationPolicy:
    """
    Returns standard multi-tier escalation chain for the given organization and event type.
    """
    if event_type == NotificationEventType.OVERDUE_ACTION:
        tiers = [
            EscalationTierConfig(
                tier=1,
                target_role="DEFENSE_ADVOCATE",
                wait_minutes=0,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            ),
            EscalationTierConfig(
                tier=2,
                target_role="SUPERVISING_LEGAL_OFFICER",
                wait_minutes=120,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.SMS],
            ),
            EscalationTierConfig(
                tier=3,
                target_role="DLSA_OFFICER",
                wait_minutes=240,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.WHATSAPP],
            ),
        ]
    elif event_type == NotificationEventType.UNRESOLVED_IDENTITY_CONFLICT:
        tiers = [
            EscalationTierConfig(
                tier=1,
                target_role="JAIL_OFFICER",
                wait_minutes=0,
                channels=[NotificationChannel.IN_APP],
            ),
            EscalationTierConfig(
                tier=2,
                target_role="SUPERVISING_LEGAL_OFFICER",
                wait_minutes=60,
                channels=[NotificationChannel.IN_APP, NotificationChannel.SMS],
            ),
            EscalationTierConfig(
                tier=3,
                target_role="PLATFORM_ADMIN",
                wait_minutes=180,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.SMS],
            ),
        ]
    elif event_type == NotificationEventType.SECURITY_EVENT:
        tiers = [
            EscalationTierConfig(
                tier=1,
                target_role="PLATFORM_ADMIN,GOV_ADMIN",
                wait_minutes=0,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.SMS],
            ),
            EscalationTierConfig(
                tier=2,
                target_role="PLATFORM_ADMIN,READ_ONLY_AUDITOR",
                wait_minutes=30,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.SMS],
            ),
        ]
    else:
        tiers = [
            EscalationTierConfig(
                tier=1,
                target_role="ALL",
                wait_minutes=0,
                channels=[NotificationChannel.IN_APP],
            ),
            EscalationTierConfig(
                tier=2,
                target_role="SUPERVISING_LEGAL_OFFICER",
                wait_minutes=240,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            ),
        ]

    policy_id = f"ESC-{org_id}-{event_type.value}"
    return EscalationPolicy(
        id=policy_id,
        org_id=org_id,
        event_type=event_type,
        tiers=tiers,
    )


class EscalationManager:
    """Manages org-specific escalation policies and calculates progression."""

    @classmethod
    def get_policy(cls, org_id: str, event_type: NotificationEventType) -> EscalationPolicy:
        key = f"{org_id}:{event_type.value}"
        if key in _ESCALATION_POLICIES:
            return _ESCALATION_POLICIES[key]

        try:
            from app.notifications.repository import NotificationRepository
            db_policy = NotificationRepository.get_escalation_policy(org_id, event_type)
            if db_policy:
                _ESCALATION_POLICIES[key] = db_policy
                return db_policy
        except Exception as e:
            logger.debug(f"Escalation policy lookup note: {e}")

        default_policy = get_default_escalation_policy(org_id, event_type)
        _ESCALATION_POLICIES[key] = default_policy
        return default_policy

    @classmethod
    def save_policy(cls, policy: EscalationPolicy):
        key = f"{policy.org_id}:{policy.event_type.value}"
        _ESCALATION_POLICIES[key] = policy
        try:
            from app.notifications.repository import NotificationRepository
            NotificationRepository.save_escalation_policy(policy)
        except Exception as e:
            logger.warning(f"Error persisting escalation policy: {e}")
        logger.info(f"Updated escalation policy for org={policy.org_id}, event={policy.event_type.value}")

    @classmethod
    def get_next_tier(
        cls,
        current_tier: int,
        policy: EscalationPolicy,
    ) -> Optional[EscalationTierConfig]:
        """
        Determines the next escalation tier in the sequence.
        Returns None if already at maximum tier.
        """
        for t in policy.tiers:
            if t.tier == current_tier + 1:
                return t
        return None

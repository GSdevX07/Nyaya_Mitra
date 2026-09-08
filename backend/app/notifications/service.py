"""
app.notifications.service — Notification Engine Facade, Escalation Dispatcher & DLQ Manager.
"""
from __future__ import annotations

import logging
import uuid
import datetime
from typing import Dict, Any, List, Optional

from app.notifications.schemas import (
    NotificationEventType,
    NotificationChannel,
    NotificationPriority,
    DeliveryStatus,
    RetryAttempt,
    NotificationRecord,
    UserNotificationPreferences,
    NotificationFilter,
)
from app.notifications.rules import compute_idempotency_key, format_event_content
from app.notifications.preferences import filter_channels_for_delivery
from app.notifications.escalation import EscalationManager
from app.notifications.adapters.base import ChannelAdapterRegistry
from app.notifications.repository import NotificationRepository

logger = logging.getLogger("nyaya_mitra.notifications.service")


class NotificationService:
    """Production service managing notifications, escalations, deduplication, and DLQ."""

    @classmethod
    def dispatch(
        cls,
        event_type: NotificationEventType,
        payload: Optional[Dict[str, Any]] = None,
        recipient: Optional[str] = None,
        case_id: Optional[str] = None,
        user_id: Optional[str] = None,
        target_role: Optional[str] = None,
        priority: Optional[NotificationPriority] = None,
        channels: Optional[List[NotificationChannel]] = None,
        org_id: str = "DEFAULT",
        escalation_tier: int = 1,
        max_retries: int = 3,
        recipient_meta: Optional[Dict[str, Any]] = None,
    ) -> NotificationRecord:
        """
        Dispatches a notification with deterministic deduplication, quiet-hours filtering,
        emergency overrides, multi-channel adapter execution, and DLQ operational task triggers.
        """
        raw_payload = dict(payload or {})
        if case_id:
            raw_payload["case_id"] = case_id
        effective_case_id = raw_payload.get("case_id") or case_id

        # 1. Resolve content, priority, and default target roles
        rule_title, rule_msg, default_prio, default_roles = format_event_content(event_type, raw_payload)
        effective_priority = priority or default_prio
        effective_role = target_role or raw_payload.get("target_role") or default_roles
        effective_user = user_id or raw_payload.get("user_id")
        effective_recipient = recipient or effective_user or effective_role

        # 2. Deterministic Idempotency Key deduplication
        fingerprint = raw_payload.get("fingerprint", "")
        entity_ref = effective_case_id or effective_user or raw_payload.get("entity_id", "GLOBAL")
        idempotency_key = compute_idempotency_key(
            event_type=event_type,
            entity_id=str(entity_ref),
            recipient=str(effective_recipient),
            fingerprint=fingerprint,
        )

        existing_record = NotificationRepository.get_by_idempotency_key(idempotency_key)
        if existing_record:
            logger.info(
                f"Reprocessed notification suppressed (idempotency key hit): "
                f"key={idempotency_key[:12]}, id={existing_record.id}"
            )
            return existing_record

        # 3. User Preferences & Quiet Hours Evaluation
        user_prefs = (
            NotificationRepository.get_user_preferences(effective_user)
            if effective_user
            else UserNotificationPreferences(user_id="default")
        )

        if channels:
            # Explicit channel request
            active_channels = channels
        else:
            # Resolved via quiet hours & emergency override
            active_channels, is_override = filter_channels_for_delivery(
                priority=effective_priority,
                event_type=event_type,
                prefs=user_prefs,
            )

        # 4. Construct Notification Record
        notif_id = f"NOTIF-{effective_case_id or 'SYS'}-{event_type.value[:6]}-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        record = NotificationRecord(
            id=notif_id,
            recipient=str(effective_recipient),
            target_role=effective_role,
            user_id=effective_user,
            case_id=effective_case_id,
            channel=active_channels[0] if active_channels else NotificationChannel.IN_APP,
            event_type=event_type,
            priority=effective_priority,
            title=rule_title,
            message=rule_msg,
            payload=raw_payload,
            created_at=now_iso,
            delivery_status=DeliveryStatus.PENDING,
            idempotency_key=idempotency_key,
            organization_id=org_id,
            escalation_tier=escalation_tier,
            is_read=False,
            is_acknowledged=False,
            is_dismissed=False,
        )

        # 5. Multi-Channel Adapter Execution with Retry Mechanism
        delivery_succeeded = False
        all_attempts: List[RetryAttempt] = []
        last_error = None

        meta = dict(recipient_meta or {})
        if user_prefs.phone_number and "phone" not in meta:
            meta["phone"] = user_prefs.phone_number
        if user_prefs.email and "email" not in meta:
            meta["email"] = user_prefs.email

        for ch in active_channels:
            adapter = ChannelAdapterRegistry.get(ch)
            if not adapter:
                logger.warning(f"No adapter registered for channel {ch.value}")
                continue

            channel_success = False
            for attempt_idx in range(1, max_retries + 1):
                attempt_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
                result = adapter.send(record, recipient_meta=meta)

                if result.success:
                    channel_success = True
                    delivery_succeeded = True
                    all_attempts.append(
                        RetryAttempt(
                            attempt_number=attempt_idx,
                            timestamp=attempt_time,
                            channel=ch,
                            success=True,
                        )
                    )
                    break
                else:
                    last_error = result.error or "Unknown delivery failure"
                    all_attempts.append(
                        RetryAttempt(
                            attempt_number=attempt_idx,
                            timestamp=attempt_time,
                            channel=ch,
                            error_message=last_error,
                            success=False,
                        )
                    )
                    if not result.retryable:
                        break

            if channel_success:
                # Primary delivery successful
                record.channel = ch
                break

        record.retry_history = all_attempts

        # 6. Evaluate Delivery Status & DLQ Trigger
        if delivery_succeeded:
            record.delivery_status = DeliveryStatus.DELIVERED
        else:
            record.delivery_status = DeliveryStatus.DEAD_LETTER
            # Route to DLQ and automatically trigger operational task for human operator
            task_id = cls._trigger_operational_dlq_task(record, last_error or "Exhausted all retries")
            NotificationRepository.save_dlq_entry(
                notification_id=record.id,
                failure_reason=last_error or "Exhausted retry budget",
                attempts=len(all_attempts),
                task_id=task_id,
            )
            logger.error(
                f"Notification {record.id} failed delivery and entered DEAD_LETTER queue. "
                f"Triggered operational task: {task_id}"
            )

        # 7. Persist and return record
        NotificationRepository.save_notification(record)
        return record

    @classmethod
    def _trigger_operational_dlq_task(
        cls,
        record: NotificationRecord,
        error_reason: str,
    ) -> str:
        """
        Creates an operational task in the universal task queue (TaskService / task_repository)
        so delivery failures are NEVER silently dropped.
        """
        task_id = f"TASK-DLQ-{record.id}"
        today_iso = datetime.date.today().isoformat()
        try:
            from app.repositories.task_repository import get_task_repository

            repo = get_task_repository()
            task_data = {
                "id": task_id,
                "case_id": record.case_id or "SYSTEM",
                "accused_name": record.payload.get("accused_name") or "System Notification Queue",
                "task_type": "NOTIFICATION_DELIVERY_FAILURE",
                "title": f"DLQ Alert: Delivery Failure for {record.title}",
                "description": (
                    f"Notification {record.id} for event {record.event_type.value} failed delivery across "
                    f"{len(record.retry_history)} attempt(s). Recipient: {record.recipient}. "
                    f"Failure Reason: {error_reason}."
                ),
                "owner_role": "PLATFORM_ADMIN",
                "owner_user_id": None,
                "owner_name": "Platform Operations",
                "priority": "HIGH",
                "due_date": today_iso,
                "source": "NOTIFICATION_DLQ",
                "reason": f"Dead-letter queue entry generated. Immediate operational remediation required.",
                "status": "PENDING_ACTION",
                "facility": "Central System",
                "district": "Central Ops",
            }
            repo.upsert_task(task_data)
            logger.info(f"Created DLQ operational task {task_id} assigned to PLATFORM_ADMIN")
        except Exception as e:
            logger.warning(f"Unable to insert DLQ operational task into task_repository: {e}")

        return task_id

    @classmethod
    def acknowledge(cls, notification_id: str, user_id: str) -> bool:
        """Acknowledges a notification without deleting audit trail."""
        return NotificationRepository.acknowledge_notification(notification_id, user_id)

    @classmethod
    def dismiss(cls, notification_id: str, user_id: str) -> bool:
        """Soft-dismisses a notification preserving full database and audit history."""
        return NotificationRepository.soft_dismiss_notification(notification_id, user_id)

    @classmethod
    def escalate(cls, notification_id: str) -> Optional[NotificationRecord]:
        """
        Escalates an unresolved notification to the next tier based on the organization policy.
        """
        record = NotificationRepository.get_by_id(notification_id)
        if not record:
            logger.warning(f"Cannot escalate: notification {notification_id} not found.")
            return None

        policy = EscalationManager.get_policy(record.organization_id, record.event_type)
        next_tier = EscalationManager.get_next_tier(record.escalation_tier, policy)
        if not next_tier:
            logger.info(f"Notification {notification_id} is already at max escalation tier {record.escalation_tier}.")
            return None

        # Build escalated payload
        esc_payload = dict(record.payload)
        esc_payload["escalated_from_id"] = record.id
        esc_payload["title"] = f"[Escalation Tier {next_tier.tier}] {record.title}"
        esc_payload["priority"] = NotificationPriority.HIGH

        escalated_record = cls.dispatch(
            event_type=record.event_type,
            payload=esc_payload,
            case_id=record.case_id,
            target_role=next_tier.target_role,
            priority=NotificationPriority.HIGH,
            channels=next_tier.channels,
            org_id=record.organization_id,
            escalation_tier=next_tier.tier,
        )
        logger.info(
            f"Escalated notification {record.id} (Tier {record.escalation_tier}) -> "
            f"{escalated_record.id} (Tier {next_tier.tier}, Role {next_tier.target_role})"
        )
        return escalated_record

    @classmethod
    def retry_dlq(cls, dlq_id: str) -> bool:
        """
        Manually retries a dead-letter queue notification.
        """
        dlq_entries = NotificationRepository.get_dlq_entries()
        target = next((e for e in dlq_entries if e["id"] == dlq_id), None)
        if not target:
            return False

        notif = NotificationRepository.get_by_id(target["notification_id"])
        if not notif:
            return False

        adapter = ChannelAdapterRegistry.get(notif.channel)
        if not adapter:
            adapter = ChannelAdapterRegistry.get(NotificationChannel.IN_APP)

        if adapter:
            res = adapter.send(notif)
            if res.success:
                notif.delivery_status = DeliveryStatus.DELIVERED
                NotificationRepository.save_notification(notif)
                target["status"] = "RESOLVED"
                logger.info(f"DLQ entry {dlq_id} successfully retried and resolved.")
                return True
        return False

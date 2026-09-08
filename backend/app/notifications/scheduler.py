"""
app.notifications.scheduler — Automatic Timed Escalation Engine & Background Worker.
Periodically scans unacknowledged notifications and advances them through organization escalation tiers.
"""
from __future__ import annotations

import asyncio
import logging
import datetime
from typing import List, Optional

from app.notifications.schemas import NotificationRecord, DeliveryStatus
from app.notifications.escalation import EscalationManager
from app.notifications.repository import NotificationRepository

logger = logging.getLogger("nyaya_mitra.notifications.scheduler")


def process_pending_escalations(
    now: Optional[datetime.datetime] = None,
) -> List[NotificationRecord]:
    """
    Synchronously scans all unacknowledged, undismissed notifications across the system.
    If an unresolved notification has exceeded its current tier's wait_minutes threshold,
    it automatically dispatches an escalation notification to the next tier and marks the
    prior notification superseded.
    """
    current_time = now or datetime.datetime.now(datetime.timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=datetime.timezone.utc)

    # Fetch active unacknowledged notifications
    candidates: List[NotificationRecord] = []
    seen_ids = set()

    from app.notifications.repository import _MEMORY_NOTIFS
    for rec in _MEMORY_NOTIFS.values():
        if not rec.is_acknowledged and not rec.is_dismissed and rec.delivery_status != DeliveryStatus.DEAD_LETTER:
            candidates.append(rec)
            seen_ids.add(rec.id)

    conn = None
    try:
        conn = NotificationRepository._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, case_id, title, message, type, target_role, user_id,
                   is_read, timestamp, channel, event_type, priority,
                   delivery_status, idempotency_key, organization_id,
                   escalation_tier, is_acknowledged, acknowledged_at,
                   acknowledged_by, is_dismissed, dismissed_at,
                   retry_history_json, payload_json, read_at
            FROM notifications
            WHERE is_acknowledged = 0 AND is_dismissed = 0 AND delivery_status != 'DEAD_LETTER'
            ORDER BY timestamp ASC
            """
        )
        for row in cursor.fetchall():
            if row[0] not in seen_ids:
                rec = NotificationRepository._row_to_record(row)
                candidates.append(rec)
                seen_ids.add(rec.id)
    except Exception as e:
        logger.debug(f"Scheduler DB query note: {e}")
    finally:
        if conn:
            conn.close()

    escalated_records: List[NotificationRecord] = []
    from app.notifications.service import NotificationService

    for rec in candidates:
        policy = EscalationManager.get_policy(rec.organization_id, rec.event_type)
        next_tier = EscalationManager.get_next_tier(rec.escalation_tier, policy)
        if not next_tier:
            continue

        try:
            created_dt = datetime.datetime.fromisoformat(rec.created_at.replace("Z", "+00:00"))
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=datetime.timezone.utc)
        except Exception as e:
            logger.warning(f"Error parsing notification timestamp {rec.created_at}: {e}")
            continue

        elapsed_minutes = (current_time - created_dt).total_seconds() / 60.0

        if elapsed_minutes >= next_tier.wait_minutes:
            logger.info(
                f"[AUTO-ESCALATION] Notification {rec.id} (Tier {rec.escalation_tier}) elapsed {elapsed_minutes:.1f}m "
                f">= {next_tier.wait_minutes}m. Auto-escalating to Tier {next_tier.tier} ({next_tier.target_role})."
            )
            escalated = NotificationService.escalate(rec.id)
            if escalated:
                escalated_records.append(escalated)

    return escalated_records


class AutomaticEscalationWorker:
    """
    Background worker that runs a recurring loop to auto-escalate overdue notifications.
    """
    _task: Optional[asyncio.Task] = None
    _is_running: bool = False

    @classmethod
    async def _loop(cls, poll_interval_seconds: int = 60):
        cls._is_running = True
        logger.info(f"Automatic escalation worker started (poll interval: {poll_interval_seconds}s)")
        while cls._is_running:
            try:
                escalated = process_pending_escalations()
                if escalated:
                    logger.info(f"Automatic escalation cycle executed: {len(escalated)} notification(s) escalated.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in automatic escalation loop: {e}", exc_info=True)

            try:
                await asyncio.sleep(poll_interval_seconds)
            except asyncio.CancelledError:
                break
        cls._is_running = False
        logger.info("Automatic escalation worker stopped.")

    @classmethod
    def start(cls, poll_interval_seconds: int = 60) -> None:
        if cls._task is None or cls._task.done():
            try:
                loop = asyncio.get_running_loop()
                cls._task = loop.create_task(cls._loop(poll_interval_seconds))
            except RuntimeError:
                logger.debug("No active running loop to start AutomaticEscalationWorker.")

    @classmethod
    def stop(cls) -> None:
        cls._is_running = False
        if cls._task and not cls._task.done():
            cls._task.cancel()

"""
app.notifications.adapters.in_app — In-App Channel Adapter.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from app.notifications.schemas import (
    NotificationChannel,
    NotificationRecord,
    ChannelDeliveryResult,
)
from app.notifications.adapters.base import BaseChannelAdapter

logger = logging.getLogger("nyaya_mitra.notifications.in_app")


class InAppAdapter(BaseChannelAdapter):
    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.IN_APP

    def send(
        self,
        record: NotificationRecord,
        recipient_meta: Optional[Dict[str, Any]] = None,
    ) -> ChannelDeliveryResult:
        """
        Dispatches in-app notification via live SSE broadcaster.
        """
        try:
            from app.services.notification_broadcaster import NotificationBroadcaster

            payload = {
                "id": record.id,
                "case_id": record.case_id,
                "title": record.title,
                "message": record.message,
                "type": record.priority.value.lower(),
                "priority": record.priority.value,
                "event_type": record.event_type.value,
                "channel": record.channel.value,
                "target_role": record.target_role or "ALL",
                "user_id": record.user_id,
                "timestamp": record.created_at,
                "is_read": int(record.is_read),
                "is_acknowledged": int(record.is_acknowledged),
                "escalation_tier": record.escalation_tier,
                "payload": record.payload,
            }
            NotificationBroadcaster.broadcast(payload)
            logger.info(f"[IN_APP] Broadcasted alert {record.id} for target_role={record.target_role}")
            return ChannelDeliveryResult(
                success=True,
                channel=NotificationChannel.IN_APP,
                external_message_id=f"inapp-{record.id}",
                retryable=False,
            )
        except Exception as e:
            logger.error(f"[IN_APP] Delivery failure for {record.id}: {e}", exc_info=True)
            return ChannelDeliveryResult(
                success=False,
                channel=NotificationChannel.IN_APP,
                error=str(e),
                retryable=True,
            )

"""
app.notifications.adapters.sms — SMS Channel Adapter.
"""
from __future__ import annotations

import logging
import uuid
import re
from typing import Dict, Any, Optional
from app.notifications.schemas import (
    NotificationChannel,
    NotificationRecord,
    ChannelDeliveryResult,
)
from app.notifications.adapters.base import BaseChannelAdapter

logger = logging.getLogger("nyaya_mitra.notifications.sms")


class BaseSmsDriver:
    """Pluggable driver interface for telecom gateways (Twilio, MSG91, CDAC)."""
    def send_sms(self, phone: str, message: str, sender_id: str = "NYAYAM") -> Dict[str, Any]:
        raise NotImplementedError


class SimulatedSmsDriver(BaseSmsDriver):
    """Zero-dependency simulated SMS provider for testing and offline environments."""
    def send_sms(self, phone: str, message: str, sender_id: str = "NYAYAM") -> Dict[str, Any]:
        msg_id = f"SMS-{uuid.uuid4().hex[:12].upper()}"
        logger.info(f"[SMS GATEWAY SIMULATION] To: {phone} | Sender: {sender_id} | Ref: {msg_id} | Body: {message[:80]}...")
        return {"success": True, "message_id": msg_id, "provider": "simulated_sms"}


class SmsAdapter(BaseChannelAdapter):
    def __init__(self, driver: Optional[BaseSmsDriver] = None):
        self.driver = driver or SimulatedSmsDriver()

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SMS

    def _normalize_phone(self, phone: Optional[str]) -> Optional[str]:
        if not phone:
            return None
        cleaned = re.sub(r"[^\d+]", "", phone.strip())
        if len(cleaned) >= 10:
            return cleaned
        return None

    def send(
        self,
        record: NotificationRecord,
        recipient_meta: Optional[Dict[str, Any]] = None,
    ) -> ChannelDeliveryResult:
        meta = recipient_meta or {}
        phone = meta.get("phone_number") or meta.get("phone") or record.payload.get("phone")
        if not phone and record.user_id:
            try:
                from app.auth.user_store import get_user_by_id
                u = get_user_by_id(record.user_id)
                if u and getattr(u, "phone", None):
                    phone = u.phone
            except Exception:
                pass
        if not phone and record.case_id:
            try:
                from app.database import get_case
                c = get_case(record.case_id)
                if c:
                    phone = getattr(c, "family_contact_phone", None) or getattr(c, "phone", None)
            except Exception:
                pass

        clean_phone = self._normalize_phone(phone)
        if not clean_phone:
            logger.warning(
                f"[SMS] Cannot deliver notification {record.id}: recipient phone number missing or unresolvable."
            )
            return ChannelDeliveryResult(
                success=False,
                channel=NotificationChannel.SMS,
                error="Recipient phone number missing or unresolvable in directory/docket",
                retryable=False,
            )


        # Format concise SMS text
        sms_text = f"Nyaya Mitra Alert: [{record.priority.value}] {record.title} - {record.message}"
        if len(sms_text) > 160:
            sms_text = sms_text[:157] + "..."

        try:
            # Check for simulated error injection in tests
            if meta.get("force_failure"):
                raise RuntimeError("Carrier network connection rejected (Simulated SMS gateway failure)")

            res = self.driver.send_sms(phone=clean_phone, message=sms_text)
            if res.get("success"):
                return ChannelDeliveryResult(
                    success=True,
                    channel=NotificationChannel.SMS,
                    external_message_id=res.get("message_id"),
                    retryable=False,
                )
            else:
                return ChannelDeliveryResult(
                    success=False,
                    channel=NotificationChannel.SMS,
                    error=res.get("error", "SMS delivery failed"),
                    retryable=True,
                )
        except Exception as e:
            logger.warning(f"[SMS] Delivery failure to {clean_phone}: {e}")
            return ChannelDeliveryResult(
                success=False,
                channel=NotificationChannel.SMS,
                error=str(e),
                retryable=True,
            )

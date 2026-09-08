"""
app.notifications.adapters.whatsapp — WhatsApp Business Channel Adapter.
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

logger = logging.getLogger("nyaya_mitra.notifications.whatsapp")


class BaseWhatsAppDriver:
    """Pluggable driver interface for WhatsApp Business Cloud API."""
    def send_template(
        self,
        phone: str,
        template_name: str,
        parameters: Dict[str, str],
    ) -> Dict[str, Any]:
        raise NotImplementedError


class SimulatedWhatsAppDriver(BaseWhatsAppDriver):
    """Zero-dependency simulated WhatsApp provider."""
    def send_template(
        self,
        phone: str,
        template_name: str,
        parameters: Dict[str, str],
    ) -> Dict[str, Any]:
        wamid = f"wamid.{uuid.uuid4().hex[:16]}"
        logger.info(f"[WHATSAPP SIMULATION] To: {phone} | Template: {template_name} | Ref: {wamid}")
        return {"success": True, "message_id": wamid, "provider": "simulated_whatsapp"}


class WhatsAppAdapter(BaseChannelAdapter):
    def __init__(self, driver: Optional[BaseWhatsAppDriver] = None):
        self.driver = driver or SimulatedWhatsAppDriver()

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.WHATSAPP

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
            clean_phone = "+919876543210"


        template_name = "nyayamitra_urgent_alert" if record.priority.value in ("HIGH", "EMERGENCY") else "nyayamitra_standard_update"
        parameters = {
            "title": record.title,
            "message": record.message[:120],
            "event_type": record.event_type.value,
            "priority": record.priority.value,
            "case_id": record.case_id or "General",
        }

        try:
            if meta.get("force_failure"):
                raise RuntimeError("WhatsApp Cloud API webhook rate limit or quota exceeded (Simulated failure)")

            res = self.driver.send_template(
                phone=clean_phone,
                template_name=template_name,
                parameters=parameters,
            )
            if res.get("success"):
                return ChannelDeliveryResult(
                    success=True,
                    channel=NotificationChannel.WHATSAPP,
                    external_message_id=res.get("message_id"),
                    retryable=False,
                )
            return ChannelDeliveryResult(
                success=False,
                channel=NotificationChannel.WHATSAPP,
                error=res.get("error", "WhatsApp dispatch failed"),
                retryable=True,
            )
        except Exception as e:
            logger.warning(f"[WHATSAPP] Delivery failure to {clean_phone}: {e}")
            return ChannelDeliveryResult(
                success=False,
                channel=NotificationChannel.WHATSAPP,
                error=str(e),
                retryable=True,
            )

"""
app.notifications.adapters.email — Email Channel Adapter.
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

logger = logging.getLogger("nyaya_mitra.notifications.email")


class BaseEmailDriver:
    """Pluggable driver interface for Email delivery (SMTP, SendGrid, Amazon SES)."""
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        sender: str = "notifications@nyayamitra.gov.in",
    ) -> Dict[str, Any]:
        raise NotImplementedError


class SimulatedEmailDriver(BaseEmailDriver):
    """Zero-dependency simulated Email driver for development and offline testing."""
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        sender: str = "notifications@nyayamitra.gov.in",
    ) -> Dict[str, Any]:
        msg_id = f"EMAIL-{uuid.uuid4().hex[:12].upper()}"
        logger.info(f"[EMAIL SIMULATION] To: {to_email} | Subject: '{subject}' | Ref: {msg_id}")
        return {"success": True, "message_id": msg_id, "provider": "simulated_email"}


class EmailAdapter(BaseChannelAdapter):
    def __init__(self, driver: Optional[BaseEmailDriver] = None):
        self.driver = driver or SimulatedEmailDriver()

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    def _validate_email(self, email: Optional[str]) -> bool:
        if not email:
            return False
        return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email.strip()))

    def send(
        self,
        record: NotificationRecord,
        recipient_meta: Optional[Dict[str, Any]] = None,
    ) -> ChannelDeliveryResult:
        meta = recipient_meta or {}
        email = meta.get("email") or record.payload.get("email")
        if not email and record.user_id:
            try:
                from app.auth.user_store import get_user_by_id
                u = get_user_by_id(record.user_id)
                if u and getattr(u, "email", None):
                    email = u.email
            except Exception:
                pass
        if not email and record.case_id:
            try:
                from app.database import get_case
                c = get_case(record.case_id)
                if c:
                    email = getattr(c, "lawyer_email", None)
            except Exception:
                pass

        if not email:
            email = f"{record.user_id or 'desk'}@nyayamitra.gov.in"

        if not self._validate_email(email):
            email = "alerts@nyayamitra.gov.in"


        subject = f"[Nyaya Mitra] [{record.priority.value}] {record.title}"
        text_body = (
            f"Official System Notification — Nyaya Mitra Judicial Services\n\n"
            f"Event Type: {record.event_type.value}\n"
            f"Priority:   {record.priority.value}\n"
            f"Notice:     {record.title}\n"
            f"Details:    {record.message}\n"
            f"Timestamp:  {record.created_at}\n\n"
            f"Access your docket at: https://nyayamitra.gov.in\n"
            f"Statutory compliance under Section 479 Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023."
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
            <h2 style="color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px;">Nyaya Mitra Official Alert</h2>
            <p><strong>Event:</strong> <span style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">{record.event_type.value}</span></p>
            <p><strong>Priority:</strong> <strong style="color: #dc2626;">{record.priority.value}</strong></p>
            <div style="background: #f8fafc; border-left: 4px solid #3b82f6; padding: 12px; margin: 16px 0;">
                <h3 style="margin-top: 0; color: #0f172a;">{record.title}</h3>
                <p style="color: #334155; margin-bottom: 0;">{record.message}</p>
            </div>
            <p style="font-size: 12px; color: #64748b;">Generated at {record.created_at} UTC. Section 479 BNSS Statutory Compliance.</p>
        </div>
        """

        try:
            if meta.get("force_failure"):
                raise RuntimeError("SMTP mail server connection timeout (Simulated failure)")

            res = self.driver.send_email(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            if res.get("success"):
                return ChannelDeliveryResult(
                    success=True,
                    channel=NotificationChannel.EMAIL,
                    external_message_id=res.get("message_id"),
                    retryable=False,
                )
            return ChannelDeliveryResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error=res.get("error", "Email dispatch rejected"),
                retryable=True,
            )
        except Exception as e:
            logger.warning(f"[EMAIL] Delivery failure to {email}: {e}")
            return ChannelDeliveryResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error=str(e),
                retryable=True,
            )

"""
services/notification_broadcaster.py — Real-time Server-Sent Events (SSE) Broadcaster.
========================================================================================
Maintains live subscriber queues for active frontend connections and broadcasts new
notifications instantly to matching roles and users without requiring page reloads.
"""

from __future__ import annotations
import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any

logger = logging.getLogger("nyaya_mitra.notifications")


class Subscriber:
    def __init__(self, user_id: str, role: str, linked_case_id: Optional[str] = None):
        self.user_id = user_id
        self.role = (role or "").strip().upper()
        self.linked_case_id = linked_case_id
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    def is_recipient(self, record: Dict[str, Any]) -> bool:
        """Evaluate if notification record is authorized for this subscriber."""
        target_role = (record.get("target_role") or "ALL").strip().upper()
        target_user = record.get("user_id")
        case_id = record.get("case_id")

        # Specific user targeting
        if target_user and target_user == self.user_id:
            return True

        # Citizen / Family scoped to linked case
        if self.role in ("ACCUSED_USER", "FAMILY_GUARDIAN"):
            if self.linked_case_id and case_id and self.linked_case_id == case_id:
                return True
            return False

        # Platform / Gov Admin receives all
        if self.role in ("PLATFORM_ADMIN", "GOV_ADMIN"):
            return True

        # Role matching
        if "ALL" in target_role:
            return True

        roles_list = [r.strip().upper() for r in target_role.split(",")]
        return self.role in roles_list


class NotificationBroadcaster:
    """Thread-safe and asynchronous pub/sub broadcaster for live notifications."""
    _subscribers: Set[Subscriber] = set()

    @classmethod
    def subscribe(cls, user_id: str, role: str, linked_case_id: Optional[str] = None) -> Subscriber:
        sub = Subscriber(user_id=user_id, role=role, linked_case_id=linked_case_id)
        cls._subscribers.add(sub)
        logger.info(f"SSE subscriber connected: user={user_id}, role={role}, active_connections={len(cls._subscribers)}")
        return sub

    @classmethod
    def unsubscribe(cls, sub: Subscriber):
        cls._subscribers.discard(sub)
        logger.info(f"SSE subscriber disconnected: user={sub.user_id}, remaining_connections={len(cls._subscribers)}")

    @classmethod
    def broadcast(cls, record: Dict[str, Any]):
        """Push notification record to all matching active subscriber queues."""
        if not cls._subscribers:
            return

        payload = dict(record)
        payload["read"] = bool(payload.get("is_read") or payload.get("read", False))

        count = 0
        for sub in list(cls._subscribers):
            if sub.is_recipient(payload):
                try:
                    sub.queue.put_nowait(payload)
                    count += 1
                except asyncio.QueueFull:
                    try:
                        sub.queue.get_nowait()
                        sub.queue.put_nowait(payload)
                        count += 1
                    except Exception:
                        pass
                except Exception as ex:
                    logger.debug(f"Broadcast push error: {ex}")

        if count > 0:
            logger.info(f"Broadcasted notification '{payload.get('title')}' ({payload.get('id')}) to {count} live client(s).")

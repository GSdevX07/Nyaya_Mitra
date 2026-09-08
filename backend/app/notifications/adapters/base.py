"""
app.notifications.adapters.base — Base Channel Adapter Interface & Registry.
"""
from __future__ import annotations

import abc
import logging
from typing import Dict, Any, Type, Optional
from app.notifications.schemas import (
    NotificationChannel,
    NotificationRecord,
    ChannelDeliveryResult,
)

logger = logging.getLogger("nyaya_mitra.notifications.adapters")


class BaseChannelAdapter(abc.ABC):
    """Abstract base adapter for delivery channels."""

    @property
    @abc.abstractmethod
    def channel(self) -> NotificationChannel:
        """The channel this adapter serves."""
        pass

    @abc.abstractmethod
    def send(
        self,
        record: NotificationRecord,
        recipient_meta: Optional[Dict[str, Any]] = None,
    ) -> ChannelDeliveryResult:
        """
        Execute dispatch through this channel provider.
        Must return ChannelDeliveryResult with success=True/False and error details.
        """
        pass


class ChannelAdapterRegistry:
    """Registry maintaining active channel adapters."""

    _adapters: Dict[NotificationChannel, BaseChannelAdapter] = {}

    @classmethod
    def register(cls, adapter: BaseChannelAdapter):
        cls._adapters[adapter.channel] = adapter
        logger.debug(f"Registered channel adapter for: {adapter.channel.value}")

    @classmethod
    def get(cls, channel: NotificationChannel) -> Optional[BaseChannelAdapter]:
        return cls._adapters.get(channel)

    @classmethod
    def get_all(cls) -> Dict[NotificationChannel, BaseChannelAdapter]:
        return dict(cls._adapters)

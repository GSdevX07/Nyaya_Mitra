"""
app.notifications.adapters — Registry bootstrap for notification adapters.
"""
from app.notifications.adapters.base import BaseChannelAdapter, ChannelAdapterRegistry
from app.notifications.adapters.in_app import InAppAdapter
from app.notifications.adapters.sms import SmsAdapter, BaseSmsDriver, SimulatedSmsDriver
from app.notifications.adapters.email import EmailAdapter, BaseEmailDriver, SimulatedEmailDriver
from app.notifications.adapters.whatsapp import WhatsAppAdapter, BaseWhatsAppDriver, SimulatedWhatsAppDriver

# Register default adapters
ChannelAdapterRegistry.register(InAppAdapter())
ChannelAdapterRegistry.register(SmsAdapter())
ChannelAdapterRegistry.register(EmailAdapter())
ChannelAdapterRegistry.register(WhatsAppAdapter())

__all__ = [
    "BaseChannelAdapter",
    "ChannelAdapterRegistry",
    "InAppAdapter",
    "SmsAdapter",
    "BaseSmsDriver",
    "SimulatedSmsDriver",
    "EmailAdapter",
    "BaseEmailDriver",
    "SimulatedEmailDriver",
    "WhatsAppAdapter",
    "BaseWhatsAppDriver",
    "SimulatedWhatsAppDriver",
]

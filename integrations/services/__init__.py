from .telegram_mtproto import TelegramMTProtoIntegration
from .whatsapp_cloud import WhatsAppCloudIntegration
from .instagram_api import InstagramMessagingIntegration
from .facebook_messenger import FacebookMessengerIntegration
from .viber import ViberIntegration
from .vk import VKIntegration

def get_adapter(integration):
    if integration.platform == "telegram": return TelegramMTProtoIntegration(integration)
    if integration.platform == "whatsapp": return WhatsAppCloudIntegration(integration)
    if integration.platform == "instagram": return InstagramMessagingIntegration(integration)
    if integration.platform == "facebook": return FacebookMessengerIntegration(integration)
    if integration.platform == "viber": return ViberIntegration(integration)
    if integration.platform == "vk": return VKIntegration(integration)
    raise ValueError("Unsupported platform")

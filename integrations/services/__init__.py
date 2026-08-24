from .telegram_mtproto import TelegramMTProtoIntegration
from .whatsapp_cloud import WhatsAppCloudIntegration
from .instagram_api import InstagramMessagingIntegration
from .facebook_messenger import FacebookMessengerIntegration

def get_adapter(integration):
    if integration.platform == "telegram": return TelegramMTProtoIntegration(integration)
    if integration.platform == "whatsapp": return WhatsAppCloudIntegration(integration)
    if integration.platform == "instagram": return InstagramMessagingIntegration(integration)
    if integration.platform == "facebook": return FacebookMessengerIntegration(integration)
    raise ValueError("Unsupported platform")

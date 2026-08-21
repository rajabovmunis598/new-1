from .telegram_mtproto import TelegramMTProtoIntegration
from .whatsapp_cloud import WhatsAppCloudIntegration

def get_adapter(integration):
    if integration.platform == "telegram": return TelegramMTProtoIntegration(integration)
    if integration.platform == "whatsapp": return WhatsAppCloudIntegration(integration)
    raise ValueError("Unsupported platform")

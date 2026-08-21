from django.urls import path
from .views import *
disconnect_tg = type("TelegramDisconnectView", (PlatformDisconnectView,), {"platform":"telegram"})
disconnect_wa = type("WhatsAppDisconnectView", (PlatformDisconnectView,), {"platform":"whatsapp"})
urlpatterns = [path("telegram/connect/start/", TelegramStartView.as_view()), path("telegram/connect/verify/", TelegramVerifyView.as_view()), path("telegram/connect/2fa/", Telegram2FAView.as_view()), path("telegram/disconnect/", disconnect_tg.as_view()), path("telegram/status/", TelegramStatusView.as_view()), path("whatsapp/connect/", WhatsAppConnectView.as_view()), path("whatsapp/disconnect/", disconnect_wa.as_view()), path("whatsapp/test/", WhatsAppTestView.as_view())]

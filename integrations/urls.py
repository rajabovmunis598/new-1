from django.urls import path

from .views import (
    FacebookOAuthCallbackView,
    FacebookOAuthStartView,
    FacebookDemoConnectView,
    InstagramOAuthCallbackView,
    InstagramOAuthStartView,
    InstagramDemoConnectView,
    PlatformDisconnectView,
    Telegram2FAView,
    TelegramStartView,
    TelegramStatusView,
    TelegramVerifyView,
    WhatsAppConnectView,
    WhatsAppTestView,
    ViberConnectView,
    VKConnectView,
    VKDemoConnectView,
    VKOAuthCompleteView,
    VKOAuthStartView,
)


disconnect_tg = type(
    "TelegramDisconnectView",
    (PlatformDisconnectView,),
    {"platform": "telegram"},
)
disconnect_wa = type(
    "WhatsAppDisconnectView",
    (PlatformDisconnectView,),
    {"platform": "whatsapp"},
)
disconnect_instagram = type(
    "InstagramDisconnectView",
    (PlatformDisconnectView,),
    {"platform": "instagram"},
)
disconnect_facebook = type(
    "FacebookDisconnectView",
    (PlatformDisconnectView,),
    {"platform": "facebook"},
)

urlpatterns = [
    path("telegram/connect/start/", TelegramStartView.as_view()),
    path("telegram/connect/verify/", TelegramVerifyView.as_view()),
    path("telegram/connect/2fa/", Telegram2FAView.as_view()),
    path("telegram/disconnect/", disconnect_tg.as_view()),
    path("telegram/status/", TelegramStatusView.as_view()),
    path("whatsapp/connect/", WhatsAppConnectView.as_view()),
    path("whatsapp/disconnect/", disconnect_wa.as_view()),
    path("whatsapp/test/", WhatsAppTestView.as_view()),
    path("viber/connect/", ViberConnectView.as_view()),
    path("vk/connect/", VKConnectView.as_view()),
    path("vk/demo/", VKDemoConnectView.as_view()),
    path("instagram/demo/", InstagramDemoConnectView.as_view()),
    path("facebook/demo/", FacebookDemoConnectView.as_view()),
    path("vk/oauth/start/", VKOAuthStartView.as_view()),
    path("vk/oauth/complete/", VKOAuthCompleteView.as_view()),
    path(
        "instagram/connect/start/",
        InstagramOAuthStartView.as_view(),
        name="instagram-oauth-start",
    ),
    path(
        "instagram/connect/callback/",
        InstagramOAuthCallbackView.as_view(),
        name="instagram-oauth-callback",
    ),
    path(
        "instagram/disconnect/",
        disconnect_instagram.as_view(),
        name="instagram-disconnect",
    ),
    path(
        "facebook/connect/start/",
        FacebookOAuthStartView.as_view(),
        name="facebook-oauth-start",
    ),
    path(
        "facebook/connect/callback/",
        FacebookOAuthCallbackView.as_view(),
        name="facebook-oauth-callback",
    ),
    path(
        "facebook/disconnect/",
        disconnect_facebook.as_view(),
        name="facebook-disconnect",
    ),
]

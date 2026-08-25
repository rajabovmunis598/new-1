"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from integrations.views import (
    FacebookWebhookView,
    InstagramWebhookView,
    IntegrationViewSet,
    WhatsAppWebhookView,
    ViberWebhookView,
    VKWebhookView,
)
from messages.views import SendMessageView
from core.views import DashboardStatisticsView, GlobalSearchView, AISuggestionsView, AITranslateView
from frontend.views import FrontendView

integration_list = IntegrationViewSet.as_view({'get':'list'})
integration_detail = IntegrationViewSet.as_view({'get':'retrieve', 'patch':'partial_update', 'delete':'destroy'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/integrations/', integration_list),
    path('api/integrations/<int:pk>/', integration_detail),
    path('api/integrations/', include('integrations.urls')),
    path('api/contacts/', include('contacts.urls')),
    path('api/conversations/', include('conversations.urls')),
    path('api/conversations/<int:pk>/messages/', SendMessageView.as_view()),
    path('api/messages/', include('messages.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/dashboard/statistics/', DashboardStatisticsView.as_view()),
    path('api/search/', GlobalSearchView.as_view(), name='global-search'),
    path('api/ai/suggestions/', AISuggestionsView.as_view(), name='ai-suggestions'),
    path('api/ai/translate/', AITranslateView.as_view(), name='ai-translate'),
    path(
        'api/webhooks/whatsapp/<int:integration_id>/',
        WhatsAppWebhookView.as_view(),
        name='whatsapp-webhook',
    ),
    path(
        'api/webhooks/instagram/',
        InstagramWebhookView.as_view(),
        name='instagram-webhook',
    ),
    path(
        'api/webhooks/facebook/',
        FacebookWebhookView.as_view(),
        name='facebook-webhook',
    ),
    path(
        'api/webhooks/viber/<int:integration_id>/',
        ViberWebhookView.as_view(),
        name='viber-webhook',
    ),
    path(
        'api/webhooks/vk/<int:integration_id>/',
        VKWebhookView.as_view(),
        name='vk-webhook',
    ),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
    path('', FrontendView.as_view(), name='frontend'),
    re_path(r'^(?!api/|admin/|static/).+$', FrontendView.as_view(), name='frontend-route'),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

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
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from integrations.views import IntegrationViewSet, WhatsAppWebhookView
from messages.views import SendMessageView
from core.views import DashboardStatisticsView

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
    path('api/webhooks/whatsapp/', WhatsAppWebhookView.as_view()),
    path('api/schema/', SpectacularAPIView.as_view()),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema')),
]

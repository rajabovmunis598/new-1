from django.urls import path
from .consumers import HubConsumer
websocket_urlpatterns=[path("ws/dashboard/", HubConsumer.as_asgi())]

import asyncio
import os
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from audit.models import IntegrationEvent
from .models import Integration
from .security import verify_meta_signature
from .serializers import IntegrationSerializer, Telegram2FASerializer, TelegramStartSerializer, TelegramVerifySerializer, WhatsAppConnectSerializer
from .services import get_adapter

class IntegrationViewSet(viewsets.ModelViewSet):
    queryset = Integration.objects.none()
    serializer_class = IntegrationSerializer
    http_method_names = ("get", "patch", "delete", "head", "options")
    filterset_fields = ("platform", "status")
    def get_queryset(self): return Integration.objects.filter(user=self.request.user)

class TelegramStartView(APIView):
    serializer_class = TelegramStartSerializer
    def post(self, request):
        s = TelegramStartSerializer(data=request.data); s.is_valid(raise_exception=True)
        obj = Integration.objects.create(user=request.user, platform="telegram", name=s.validated_data["name"], status="pending")
        try: asyncio.run(get_adapter(obj).start(s.validated_data["phone"]))
        except Exception:
            obj.delete(); raise
        return Response({"integration_id":obj.id, "status":"code_sent"}, status=201)

class TelegramVerifyView(APIView):
    serializer_class = TelegramVerifySerializer
    def post(self, request):
        s = self.serializer_class(data=request.data); s.is_valid(raise_exception=True)
        obj = get_object_or_404(Integration, id=s.validated_data["integration_id"], user=request.user, platform="telegram")
        result = asyncio.run(get_adapter(obj).verify(s.validated_data["code"]))
        return Response({"integration":IntegrationSerializer(obj).data, **result})

class Telegram2FAView(APIView):
    serializer_class = Telegram2FASerializer
    def post(self, request):
        s = Telegram2FASerializer(data=request.data); s.is_valid(raise_exception=True)
        obj = get_object_or_404(Integration, id=s.validated_data["integration_id"], user=request.user, platform="telegram")
        asyncio.run(get_adapter(obj).verify_2fa(s.validated_data["password"])); return Response(IntegrationSerializer(obj).data)

class PlatformDisconnectView(APIView):
    platform = None
    def post(self, request):
        obj = get_object_or_404(Integration, id=request.data.get("integration_id"), user=request.user, platform=self.platform)
        get_adapter(obj).disconnect(); return Response(status=204)

class TelegramStatusView(APIView):
    def get(self, request):
        obj = Integration.objects.filter(user=request.user, platform="telegram").first()
        return Response(IntegrationSerializer(obj).data if obj else {"status":"inactive"})

class WhatsAppConnectView(APIView):
    serializer_class = WhatsAppConnectSerializer
    def post(self, request):
        s = WhatsAppConnectSerializer(data=request.data); s.is_valid(raise_exception=True); data = s.validated_data
        obj = Integration(user=request.user, platform="whatsapp", name=data.pop("name"), status="active", external_account_id=data["phone_number_id"])
        obj.set_credentials(data); obj.save(); return Response(IntegrationSerializer(obj).data, status=201)

class WhatsAppTestView(APIView):
    def post(self, request):
        obj = get_object_or_404(Integration, id=request.data.get("integration_id"), user=request.user, platform="whatsapp")
        return Response({"ok":bool(obj.get_credentials().get("access_token")), "status":obj.status})

class WhatsAppWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    def get(self, request):
        token = request.query_params.get("hub.verify_token")
        if request.query_params.get("hub.mode") == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN", ""):
            return Response(int(request.query_params.get("hub.challenge", 0)))
        return Response({"detail":"Verification failed"}, status=403)
    def post(self, request):
        secret = os.getenv("WHATSAPP_APP_SECRET", "")
        if not verify_meta_signature(request.body, request.headers.get("X-Hub-Signature-256"), secret): return Response({"detail":"Invalid signature"}, status=403)
        accepted = 0
        from .tasks import process_whatsapp_event
        for entry in request.data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {}); phone_id = value.get("metadata", {}).get("phone_number_id")
                integration = Integration.objects.filter(platform="whatsapp", external_account_id=phone_id, status="active").first()
                if not integration: continue
                for msg in value.get("messages", []):
                    event_id = msg.get("id", "")
                    event, created = IntegrationEvent.objects.get_or_create(integration=integration, external_event_id=event_id, defaults={"event_type":"message", "payload":{"message":msg, "contacts":value.get("contacts", [])}})
                    if created: process_whatsapp_event.delay(event.id); accepted += 1
        return Response({"accepted":accepted})

from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from .models import Integration


class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = (
            "id",
            "platform",
            "name",
            "status",
            "external_account_id",
            "webhook_url",
            "last_sync_at",
            "last_error",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "platform",
            "status",
            "external_account_id",
            "webhook_url",
            "last_sync_at",
            "last_error",
            "created_at",
            "updated_at",
        )

    def get_webhook_url(self, obj):
        """Return a publicly reachable WhatsApp webhook URL.

        The URL is recomputed from the current request host (or SITE_URL)
        instead of trusting the value captured at connect time, so the URL
        shown in the UI always matches the domain the admin is using (e.g. the
        public tunnel host) and Meta can actually deliver webhooks to it.
        """
        if obj.platform != "whatsapp" or not obj.pk:
            return obj.webhook_url
        path = reverse("whatsapp-webhook", kwargs={"integration_id": obj.pk})
        configured = str(getattr(settings, "WHATSAPP_WEBHOOK_BASE_URL", "")).strip()
        if configured:
            return configured.rstrip("/") + path
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(path)
        site = str(getattr(settings, "SITE_URL", "")).strip()
        if site:
            return site.rstrip("/") + path
        return obj.webhook_url


class TelegramStartSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=255, default="Telegram")
    api_id = serializers.IntegerField(min_value=1, write_only=True)
    api_hash = serializers.RegexField(
        r"^[0-9a-fA-F]{32}$",
        write_only=True,
        error_messages={
            "invalid": "API Hash бояд аз 32 аломати hexadecimal иборат бошад."
        },
    )


class TelegramVerifySerializer(serializers.Serializer):
    integration_id = serializers.IntegerField()
    code = serializers.CharField(max_length=16)


class Telegram2FASerializer(serializers.Serializer):
    integration_id = serializers.IntegerField()
    password = serializers.CharField(write_only=True)


class IntegrationIDSerializer(serializers.Serializer):
    integration_id = serializers.IntegerField()


class TelegramStartResponseSerializer(serializers.Serializer):
    integration_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=("code_sent",))


class TelegramVerifyResponseSerializer(serializers.Serializer):
    integration = IntegrationSerializer()
    requires_2fa = serializers.BooleanField()


class WhatsAppTestResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    status = serializers.CharField()


class WhatsAppConnectSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, default="WhatsApp")
    access_token = serializers.CharField(write_only=True, min_length=8)
    phone_number_id = serializers.RegexField(r"^\d+$")
    business_account_id = serializers.RegexField(
        r"^\d+$",
        required=False,
        allow_blank=True,
    )
    app_secret = serializers.CharField(write_only=True, min_length=8)
    verify_token = serializers.CharField(write_only=True, min_length=8, max_length=255)


class InstagramOAuthStartSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, default="Instagram")
    app_id = serializers.CharField(max_length=64, write_only=True, required=False)
    app_secret = serializers.CharField(min_length=8, write_only=True, required=False)
    verify_token = serializers.CharField(min_length=8, max_length=255, write_only=True, required=False)


class InstagramOAuthStartResponseSerializer(serializers.Serializer):
    authorization_url = serializers.URLField()
    expires_in = serializers.IntegerField(min_value=1)


class InstagramOAuthCallbackSerializer(serializers.Serializer):
    state = serializers.CharField(max_length=2048)
    code = serializers.CharField(max_length=2048, required=False)
    error = serializers.CharField(max_length=255, required=False)

    def validate(self, attrs):
        if not attrs.get("code") and not attrs.get("error"):
            raise serializers.ValidationError("Instagram authorization response is incomplete.")
        return attrs


class FacebookOAuthStartSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, default="Facebook")
    app_id = serializers.CharField(max_length=64, write_only=True, required=False)
    app_secret = serializers.CharField(min_length=8, write_only=True, required=False)
    verify_token = serializers.CharField(min_length=8, max_length=255, write_only=True, required=False)


class FacebookOAuthStartResponseSerializer(serializers.Serializer):
    authorization_url = serializers.URLField()
    expires_in = serializers.IntegerField(min_value=1)


class FacebookOAuthCallbackSerializer(serializers.Serializer):
    state = serializers.CharField(max_length=2048)
    code = serializers.CharField(max_length=2048, required=False)
    error = serializers.CharField(max_length=255, required=False)

    def validate(self, attrs):
        if not attrs.get("code") and not attrs.get("error"):
            raise serializers.ValidationError("Facebook authorization response is incomplete.")
        return attrs

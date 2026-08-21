from rest_framework import serializers
from .models import Integration

class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        exclude = ("credentials", "session_data")
        read_only_fields = ("user", "platform", "status", "external_account_id", "last_sync_at", "last_error")

class TelegramStartSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=255, default="Telegram")

class TelegramVerifySerializer(serializers.Serializer):
    integration_id = serializers.IntegerField()
    code = serializers.CharField(max_length=16)

class Telegram2FASerializer(serializers.Serializer):
    integration_id = serializers.IntegerField()
    password = serializers.CharField(write_only=True)

class WhatsAppConnectSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, default="WhatsApp")
    access_token = serializers.CharField(write_only=True)
    phone_number_id = serializers.CharField()
    business_account_id = serializers.CharField(required=False, allow_blank=True)
    app_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    verify_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

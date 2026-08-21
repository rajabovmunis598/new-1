from rest_framework import serializers
from .models import Message

class MessageSerializer(serializers.ModelSerializer):
    platform = serializers.CharField(source="conversation.integration.platform", read_only=True)
    class Meta:
        model = Message
        fields = "__all__"
        read_only_fields = ("conversation", "external_message_id", "sender_type", "external_created_at", "metadata")

class OutgoingMessageSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4096)

from rest_framework import serializers
from django.utils import timezone

from contacts.serializers import ContactSerializer
from .models import Conversation, ConversationNote


class ConversationSerializer(serializers.ModelSerializer):
    contact_detail = ContactSerializer(source="contact", read_only=True)
    platform = serializers.CharField(source="integration.platform", read_only=True)
    unread_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Conversation
        fields = (
            "id",
            "integration",
            "contact",
            "contact_detail",
            "platform",
            "external_chat_id",
            "title",
            "status",
            "is_pinned",
            "priority",
            "snoozed_until",
            "unread_count",
            "last_message_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("integration", "contact", "external_chat_id")

    def validate_snoozed_until(self, value):
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError("Snooze time must be in the future.")
        return value


class ConversationSnoozeSerializer(serializers.Serializer):
    snoozed_until = serializers.DateTimeField()

    def validate_snoozed_until(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Snooze time must be in the future.")
        return value


class ConversationReadResponseSerializer(serializers.Serializer):
    updated = serializers.IntegerField(read_only=True)
    unread_count = serializers.IntegerField(read_only=True)


class ConversationNoteSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(
        source="author.username",
        read_only=True,
    )

    class Meta:
        model = ConversationNote
        fields = (
            "id",
            "conversation",
            "author",
            "author_username",
            "text",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "conversation",
            "author",
            "author_username",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "text": {
                "min_length": 1,
                "max_length": 5000,
                "trim_whitespace": True,
            }
        }

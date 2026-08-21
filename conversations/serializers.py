from rest_framework import serializers
from contacts.serializers import ContactSerializer
from .models import Conversation

class ConversationSerializer(serializers.ModelSerializer):
    contact_detail = ContactSerializer(source="contact", read_only=True)
    platform = serializers.CharField(source="integration.platform", read_only=True)
    unread_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Conversation
        fields = "__all__"
        read_only_fields = ("integration", "contact", "external_chat_id")

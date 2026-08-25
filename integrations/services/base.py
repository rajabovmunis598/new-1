import uuid

from django.db import transaction
from django.utils import timezone

from integrations.processing import advance_conversation_last_message
from messages.models import Message


class BaseIntegration:
    def __init__(self, integration):
        self.integration = integration

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        self.integration.status = "inactive"
        self.integration.session_data = ""
        self.integration.save(
            update_fields=["status", "session_data", "updated_at"]
        )

    def send_message(self, conversation, text):
        raise NotImplementedError

    def process_event(self, payload):
        raise NotImplementedError

    def get_external_url(self, message):
        return None

    def save_outgoing(
        self,
        conversation,
        text,
        external_id=None,
        metadata=None,
        external_created_at=None,
        sender_type="business",
    ):
        timestamp = external_created_at or timezone.now()
        external_key = str(external_id) if external_id not in (None, "") else ""
        defaults = {
            "sender_type": sender_type,
            "text": text,
            "external_created_at": timestamp,
            "metadata": metadata or {},
        }
        with transaction.atomic():
            if external_key:
                message, _ = Message.objects.update_or_create(
                    conversation=conversation,
                    external_message_id=external_key,
                    defaults=defaults,
                )
            else:
                message = Message.objects.create(
                    conversation=conversation,
                    external_message_id=f"local-{uuid.uuid4()}",
                    **defaults,
                )
            advance_conversation_last_message(conversation, timestamp)
        return message

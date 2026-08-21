import uuid
from django.utils import timezone
from messages.models import Message

class BaseIntegration:
    def __init__(self, integration): self.integration = integration
    def connect(self): raise NotImplementedError
    def disconnect(self):
        self.integration.status = "inactive"; self.integration.session_data = ""; self.integration.save(update_fields=["status", "session_data", "updated_at"])
    def send_message(self, conversation, text): raise NotImplementedError
    def process_event(self, payload): raise NotImplementedError
    def get_external_url(self, message): return None
    def save_outgoing(self, conversation, text, external_id=None, metadata=None):
        message = Message.objects.create(conversation=conversation, external_message_id=external_id or f"local-{uuid.uuid4()}", sender_type="business", text=text, external_created_at=timezone.now(), metadata=metadata or {})
        conversation.last_message_at = message.external_created_at; conversation.save(update_fields=["last_message_at", "updated_at"])
        return message

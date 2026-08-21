from datetime import datetime, timezone as dt_timezone
from django.db import transaction
from django.utils import timezone
from contacts.models import Contact
from conversations.models import Conversation
from messages.models import Message
from notifications.models import Notification

@transaction.atomic
def persist_incoming(integration, data):
    contact_id = str(data.get("contact_id") or data.get("from") or data.get("chat_id") or "unknown")
    contact, _ = Contact.objects.update_or_create(integration=integration, external_id=contact_id, defaults={"name": data.get("name", ""), "username": data.get("username", ""), "phone": data.get("phone", data.get("from", ""))})
    chat_id = str(data.get("chat_id") or contact_id)
    conversation, _ = Conversation.objects.get_or_create(integration=integration, external_chat_id=chat_id, defaults={"contact": contact, "title": data.get("name", "")})
    external_id = str(data.get("message_id") or data.get("id") or "")
    message, created = Message.objects.get_or_create(conversation=conversation, external_message_id=external_id, defaults={"sender_type":data.get("sender_type", "customer"), "message_type":data.get("type", "text") if data.get("type") in dict(Message.MESSAGE_TYPE_CHOICES) else "other", "text":data.get("text", ""), "media_url":data.get("media_url", ""), "external_created_at":data.get("timestamp") or timezone.now(), "metadata":data})
    if created:
        conversation.last_message_at = message.external_created_at or message.created_at; conversation.save(update_fields=["last_message_at", "updated_at"])
        Notification.objects.create(user=integration.user, type="new_message", title=f"New {integration.platform} message", message=message.text[:255])
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            async_to_sync(get_channel_layer().group_send)(f"user_{integration.user_id}", {"type":"hub.event", "event":{"type":"new_message", "message_id":message.id}})
        except (ImportError, AttributeError): pass
    return message, created

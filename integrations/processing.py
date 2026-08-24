from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from contacts.models import Contact
from conversations.models import Conversation
from messages.models import Message
from notifications.models import Notification


def _message_timestamp(value):
    if isinstance(value, str):
        value = parse_datetime(value)
    if not isinstance(value, datetime):
        return timezone.now()
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _public_metadata(data):
    metadata = {
        key: value
        for key, value in data.items()
        if not key.startswith("_")
    }
    timestamp = metadata.get("timestamp")
    if isinstance(timestamp, datetime):
        metadata["timestamp"] = timestamp.isoformat()
    return metadata


def _broadcast_new_message(user_id, message_id, conversation_id, platform):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "hub.event",
                "event": {
                    "type": "new_message",
                    "message_id": message_id,
                    "conversation_id": conversation_id,
                    "platform": platform,
                },
            },
        )
    except (ImportError, AttributeError):
        pass


def advance_conversation_last_message(conversation, timestamp):
    """Move a conversation's activity timestamp forward, never backward."""
    if timestamp is None:
        return False
    updated = Conversation.objects.filter(pk=conversation.pk).filter(
        Q(last_message_at__isnull=True) | Q(last_message_at__lt=timestamp)
    ).update(last_message_at=timestamp, updated_at=timezone.now())
    if updated:
        conversation.last_message_at = timestamp
    return bool(updated)


@transaction.atomic
def persist_incoming(integration, data):
    contact_id = str(
        data.get("contact_id")
        or data.get("from")
        or data.get("chat_id")
        or "unknown"
    )
    contact, _ = Contact.objects.update_or_create(
        integration=integration,
        external_id=contact_id,
        defaults={
            "name": data.get("name", ""),
            "username": data.get("username", ""),
            "phone": data.get("phone", data.get("from", "")),
        },
    )

    chat_id = str(data.get("chat_id") or contact_id)
    conversation, conversation_created = Conversation.objects.get_or_create(
        integration=integration,
        external_chat_id=chat_id,
        defaults={
            "contact": contact,
            "title": data.get("chat_name") or data.get("name", ""),
        },
    )
    conversation_updates = []
    peer = data.get("_telegram_peer")
    if peer:
        conversation.set_external_peer(peer)
        conversation_updates.append("external_peer_data")
    chat_name = data.get("chat_name")
    if chat_name and conversation.title != chat_name:
        conversation.title = chat_name
        conversation_updates.append("title")
    if conversation_updates:
        conversation.save(update_fields=[*conversation_updates, "updated_at"])

    external_id = str(data.get("message_id") or data.get("id") or "")
    message_type = data.get("type", "text")
    if message_type not in dict(Message.MESSAGE_TYPE_CHOICES):
        message_type = "other"
    message, created = Message.objects.get_or_create(
        conversation=conversation,
        external_message_id=external_id,
        defaults={
            "sender_type": data.get("sender_type", "customer"),
            "message_type": message_type,
            "text": data.get("text", ""),
            "media_url": data.get("media_url", ""),
            "external_created_at": _message_timestamp(data.get("timestamp")),
            "metadata": _public_metadata(data),
        },
    )
    if created:
        advance_conversation_last_message(
            conversation,
            message.external_created_at or message.created_at,
        )
        if message.sender_type == "customer":
            Notification.objects.create(
                user=integration.user,
                type="new_message",
                title=f"New {integration.platform} message",
                message=message.text[:255],
            )
            transaction.on_commit(
                lambda: _broadcast_new_message(
                    integration.user_id,
                    message.id,
                    conversation.id,
                    integration.platform,
                )
            )
    return message, created

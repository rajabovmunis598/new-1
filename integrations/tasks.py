from datetime import datetime, timedelta, timezone as datetime_timezone
from django.db import transaction
from django.utils import timezone
from audit.models import IntegrationEvent

try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(fn):
            if kwargs.get("bind"):
                fn.delay = lambda *a, **kw: fn(None, *a, **kw)
            else:
                fn.delay = fn
            return fn
        return decorator

def _process_whatsapp_event(event_id):
    """Process one WhatsApp webhook event synchronously.

    Shared by the Celery task and the synchronous webhook fallback, so a
    WhatsApp message always lands in the database even when no Celery
    worker is running.
    """
    event = IntegrationEvent.objects.select_related("integration").get(pk=event_id)
    if event.status == "processed":
        return event_id
    event.status = "processing"
    event.save(update_fields=["status"])
    try:
        msg = event.payload["message"]
        contact = (event.payload.get("contacts") or [{}])[0]
        text = msg.get("text", {}).get("body", "")
        data = {
            "id": msg.get("id"),
            "from": msg.get("from"),
            "phone": msg.get("from"),
            "name": contact.get("profile", {}).get("name", ""),
            "type": msg.get("type", "other"),
            "text": text,
            "timestamp": timezone.datetime.fromtimestamp(
                int(msg.get("timestamp", timezone.now().timestamp())),
                tz=timezone.get_current_timezone(),
            ),
        }
        from .services import get_adapter

        get_adapter(event.integration).process_event(data)
        event.status = "processed"
        event.processed_at = timezone.now()
        event.error_message = ""
    except Exception as exc:
        event.status = "failed"
        event.error_message = str(exc)[:2000]
        event.save()
        raise
    event.save()
    return event_id


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_whatsapp_event(self, event_id):
    return _process_whatsapp_event(event_id)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_telegram_event(self, event_id):
    event = IntegrationEvent.objects.select_related("integration").get(pk=event_id)
    from .telegram_runtime import process_stored_telegram_event
    return process_stored_telegram_event(event)


def _instagram_timestamp(value):
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return timezone.now()
    if raw > 100_000_000_000:
        raw /= 1000
    try:
        return datetime.fromtimestamp(raw, tz=datetime_timezone.utc)
    except (OverflowError, OSError, ValueError):
        return timezone.now()


def _normalize_instagram_event(event, adapter):
    messaging = event.payload.get("messaging") or {}
    if not isinstance(messaging, dict):
        raise ValueError("Invalid Instagram messaging event.")
    sender_id = str((messaging.get("sender") or {}).get("id") or "")
    if not sender_id:
        raise ValueError("Instagram sender is missing.")

    message = messaging.get("message") or {}
    postback = messaging.get("postback") or {}
    if not isinstance(message, dict) or not isinstance(postback, dict):
        raise ValueError("Invalid Instagram message.")
    profile = adapter.get_user_profile(sender_id) or {}
    if not isinstance(profile, dict):
        profile = {}

    text = str(message.get("text") or postback.get("title") or "")
    message_type = "text" if text else "other"
    media_url = ""
    attachments = message.get("attachments") or []
    if (
        isinstance(attachments, list)
        and attachments
        and isinstance(attachments[0], dict)
    ):
        attachment = attachments[0]
        attachment_type = str(attachment.get("type") or "")
        message_type = {
            "image": "image",
            "video": "video",
            "audio": "audio",
            "file": "document",
        }.get(attachment_type, "other")
        attachment_payload = attachment.get("payload") or {}
        if isinstance(attachment_payload, dict):
            media_url = str(attachment_payload.get("url") or "")

    return {
        "id": event.external_event_id,
        "message_id": event.external_event_id,
        "from": sender_id,
        "contact_id": sender_id,
        "chat_id": sender_id,
        "phone": "",
        "name": str(profile.get("name") or profile.get("username") or ""),
        "username": str(profile.get("username") or ""),
        "type": message_type,
        "text": text,
        "media_url": media_url,
        "timestamp": _instagram_timestamp(messaging.get("timestamp")),
        "sender_type": "customer",
        "instagram_recipient_id": str(
            (messaging.get("recipient") or {}).get("id") or ""
        ),
    }


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_instagram_event(self, event_id):
    with transaction.atomic():
        event = (
            IntegrationEvent.objects.select_for_update()
            .select_related("integration")
            .get(pk=event_id)
        )
        if event.status not in {"received", "failed"}:
            return event_id
        if event.integration.platform != "instagram":
            raise ValueError("Integration event is not an Instagram event.")
        event.status = "processing"
        event.error_message = ""
        event.save(update_fields=["status", "error_message"])
    try:
        from .services import get_adapter

        adapter = get_adapter(event.integration)
        adapter.process_event(_normalize_instagram_event(event, adapter))
        event.status = "processed"
        event.processed_at = timezone.now()
        event.error_message = ""
        event.save(
            update_fields=["status", "processed_at", "error_message"]
        )
    except Exception as exc:
        event.status = "failed"
        event.error_message = str(exc)[:2000]
        event.save(update_fields=["status", "error_message"])
        raise
    return event_id


def _normalize_facebook_event(event, adapter):
    messaging = event.payload.get("messaging") or {}
    if not isinstance(messaging, dict):
        raise ValueError("Invalid Facebook messaging event.")
    sender_id = str((messaging.get("sender") or {}).get("id") or "")
    if not sender_id:
        raise ValueError("Facebook sender is missing.")

    message = messaging.get("message") or {}
    postback = messaging.get("postback") or {}
    if not isinstance(message, dict) or not isinstance(postback, dict):
        raise ValueError("Invalid Facebook message.")
    profile = adapter.get_user_profile(sender_id) or {}
    if not isinstance(profile, dict):
        profile = {}

    text = str(message.get("text") or postback.get("title") or "")
    message_type = "text" if text else "other"
    media_url = ""
    attachments = message.get("attachments") or []
    if (
        isinstance(attachments, list)
        and attachments
        and isinstance(attachments[0], dict)
    ):
        attachment = attachments[0]
        attachment_type = str(attachment.get("type") or "")
        message_type = {
            "image": "image",
            "video": "video",
            "audio": "audio",
            "file": "document",
        }.get(attachment_type, "other")
        attachment_payload = attachment.get("payload") or {}
        if isinstance(attachment_payload, dict):
            media_url = str(attachment_payload.get("url") or "")

    return {
        "id": event.external_event_id,
        "message_id": event.external_event_id,
        "from": sender_id,
        "contact_id": sender_id,
        "chat_id": sender_id,
        "phone": "",
        "name": str(profile.get("name") or ""),
        "username": "",
        "type": message_type,
        "text": text,
        "media_url": media_url,
        "timestamp": _instagram_timestamp(messaging.get("timestamp")),
        "sender_type": "customer",
        "facebook_recipient_id": str(
            (messaging.get("recipient") or {}).get("id") or ""
        ),
    }


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_facebook_event(self, event_id):
    with transaction.atomic():
        event = (
            IntegrationEvent.objects.select_for_update()
            .select_related("integration")
            .get(pk=event_id)
        )
        if event.status not in {"received", "failed"}:
            return event_id
        if event.integration.platform != "facebook":
            raise ValueError("Integration event is not a Facebook event.")
        event.status = "processing"
        event.error_message = ""
        event.save(update_fields=["status", "error_message"])
    try:
        from .services import get_adapter

        adapter = get_adapter(event.integration)
        adapter.process_event(_normalize_facebook_event(event, adapter))
        event.status = "processed"
        event.processed_at = timezone.now()
        event.error_message = ""
        event.save(
            update_fields=["status", "processed_at", "error_message"]
        )
    except Exception as exc:
        event.status = "failed"
        event.error_message = str(exc)[:2000]
        event.save(update_fields=["status", "error_message"])
        raise
    return event_id

@shared_task
def retry_failed_event():
    events = IntegrationEvent.objects.filter(
        status="failed",
        created_at__gte=timezone.now()-timedelta(days=7),
    ).select_related("integration")[:100]
    for event in events:
        if event.integration.platform == "telegram":
            process_telegram_event.delay(event.id)
        elif event.integration.platform == "whatsapp":
            process_whatsapp_event.delay(event.id)
        elif event.integration.platform == "instagram":
            process_instagram_event.delay(event.id)
        elif event.integration.platform == "facebook":
            process_facebook_event.delay(event.id)

@shared_task
def cleanup_old_events(): return IntegrationEvent.objects.filter(created_at__lt=timezone.now()-timedelta(days=30)).delete()[0]

@shared_task
def check_integrations(): return None

@shared_task
def generate_statistics(): return None

from datetime import timedelta
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

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_whatsapp_event(self, event_id):
    event = IntegrationEvent.objects.select_related("integration").get(pk=event_id)
    if event.status == "processed": return event_id
    event.status = "processing"; event.save(update_fields=["status"])
    try:
        msg = event.payload["message"]; contact = (event.payload.get("contacts") or [{}])[0]
        text = msg.get("text", {}).get("body", "")
        data = {"id":msg.get("id"), "from":msg.get("from"), "phone":msg.get("from"), "name":contact.get("profile", {}).get("name", ""), "type":msg.get("type", "other"), "text":text, "timestamp":timezone.datetime.fromtimestamp(int(msg.get("timestamp", timezone.now().timestamp())), tz=timezone.get_current_timezone())}
        from .services import get_adapter
        get_adapter(event.integration).process_event(data); event.status="processed"; event.processed_at=timezone.now(); event.error_message=""
    except Exception as exc:
        event.status="failed"; event.error_message=str(exc)[:2000]; event.save(); raise
    event.save(); return event_id

@shared_task
def process_telegram_event(event_id):
    event = IntegrationEvent.objects.select_related("integration").get(pk=event_id)
    from .services import get_adapter
    get_adapter(event.integration).process_event(event.payload)
    event.status="processed"; event.processed_at=timezone.now(); event.save(); return event_id

@shared_task
def retry_failed_event():
    for event in IntegrationEvent.objects.filter(status="failed", created_at__gte=timezone.now()-timedelta(days=7))[:100]: process_whatsapp_event.delay(event.id)

@shared_task
def cleanup_old_events(): return IntegrationEvent.objects.filter(created_at__lt=timezone.now()-timedelta(days=30)).delete()[0]

@shared_task
def check_integrations(): return None

@shared_task
def generate_statistics(): return None

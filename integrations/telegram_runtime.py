import asyncio
import inspect
import logging
from contextlib import suppress

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from audit.models import IntegrationEvent

from .models import Integration
from .security import decrypt_json, encrypt_json
from .services import get_adapter


logger = logging.getLogger(__name__)

TERMINAL_SESSION_ERRORS = {
    "AuthKeyDuplicatedError",
    "AuthKeyUnregisteredError",
    "SessionRevokedError",
    "UserDeactivatedBanError",
    "UserDeactivatedError",
}


async def _maybe_await(value):
    return await value if inspect.isawaitable(value) else value


def _message_type(message):
    if getattr(message, "sticker", None):
        return "sticker"
    if getattr(message, "video", None):
        return "video"
    if getattr(message, "voice", None) or getattr(message, "audio", None):
        return "audio"
    if getattr(message, "photo", None):
        return "image"
    if getattr(message, "document", None):
        return "document"
    if getattr(message, "geo", None):
        return "location"
    return "text" if getattr(message, "raw_text", "") else "other"


def _display_name(entity):
    if entity is None:
        return ""
    try:
        from telethon.utils import get_display_name

        display_name = get_display_name(entity)
        if display_name:
            return display_name
    except (ImportError, TypeError, AttributeError):
        pass
    parts = (
        getattr(entity, "first_name", ""),
        getattr(entity, "last_name", ""),
    )
    return (
        " ".join(part for part in parts if part)
        or getattr(entity, "title", "")
        or ""
    )


def _serialize_input_peer(peer):
    if peer is None:
        return None

    peer_name = peer.__class__.__name__
    if peer_name == "InputPeerUser":
        peer_type = "user"
        peer_id = getattr(peer, "user_id", None)
    elif peer_name == "InputPeerChat":
        peer_type = "chat"
        peer_id = getattr(peer, "chat_id", None)
    elif peer_name == "InputPeerChannel":
        peer_type = "channel"
        peer_id = getattr(peer, "channel_id", None)
    else:
        return None

    if peer_id is None:
        return None
    value = {"type": peer_type, "id": peer_id}
    access_hash = getattr(peer, "access_hash", None)
    if access_hash is not None:
        value["access_hash"] = access_hash
    return value


async def normalize_telegram_event(event):
    """Convert a Telethon NewMessage event into JSON-safe application data."""
    message = getattr(event, "message", event)
    message_id = getattr(event, "id", None) or getattr(message, "id", None)
    chat_id = getattr(event, "chat_id", None)
    sender_id = getattr(event, "sender_id", None)
    if message_id is None or chat_id is None:
        raise ValueError("Telegram event has no message_id or chat_id")

    sender = None
    get_sender = getattr(event, "get_sender", None)
    if callable(get_sender):
        try:
            sender = await _maybe_await(get_sender())
        except Exception:
            logger.warning(
                "Could not resolve Telegram sender for chat=%s message=%s",
                chat_id,
                message_id,
            )

    chat = None
    get_chat = getattr(event, "get_chat", None)
    if callable(get_chat):
        try:
            chat = await _maybe_await(get_chat())
        except Exception:
            logger.warning(
                "Could not resolve Telegram chat for chat=%s message=%s",
                chat_id,
                message_id,
            )

    input_peer = None
    get_input_chat = getattr(event, "get_input_chat", None)
    if callable(get_input_chat):
        try:
            input_peer = await _maybe_await(get_input_chat())
        except Exception:
            logger.warning(
                "Could not resolve Telegram peer for chat=%s message=%s",
                chat_id,
                message_id,
            )

    event_date = getattr(event, "date", None) or getattr(message, "date", None)
    timestamp = event_date.isoformat() if hasattr(event_date, "isoformat") else None
    text = getattr(event, "raw_text", None)
    if text is None:
        text = getattr(message, "raw_text", "") or getattr(message, "message", "")

    contact_id = sender_id if sender_id is not None else chat_id
    payload = {
        "id": str(message_id),
        "message_id": str(message_id),
        "chat_id": str(chat_id),
        "contact_id": str(contact_id),
        "from": str(contact_id),
        "sender_type": "customer",
        "name": _display_name(sender),
        "username": getattr(sender, "username", "") or "",
        "phone": getattr(sender, "phone", "") or "",
        "type": _message_type(message),
        "text": text or "",
    }
    if timestamp:
        payload["timestamp"] = timestamp
    chat_name = _display_name(chat)
    if chat_name:
        payload["chat_name"] = chat_name

    peer = _serialize_input_peer(input_peer)
    if peer:
        payload["_telegram_peer"] = peer
    return payload


def _stored_payload(payload):
    value = dict(payload)
    peer = value.pop("_telegram_peer", None)
    # Never persist a raw peer access_hash in IntegrationEvent.payload.
    value.pop("_telegram_peer_encrypted", None)
    if peer:
        value["_telegram_peer_encrypted"] = encrypt_json(peer)
    return value


def restore_telegram_event_payload(payload):
    value = dict(payload or {})
    value.pop("_telegram_peer", None)
    encrypted_peer = value.pop("_telegram_peer_encrypted", "")
    if encrypted_peer:
        peer = decrypt_json(encrypted_peer)
        if isinstance(peer, dict) and peer.get("type") in {"user", "chat", "channel"}:
            value["_telegram_peer"] = peer
    return value


def process_stored_telegram_event(event):
    """Idempotently persist a stored Telegram event into hub models."""
    with transaction.atomic():
        event = (
            IntegrationEvent.objects.select_for_update()
            .select_related("integration")
            .get(pk=event.pk)
        )
        if event.status not in {"received", "failed"}:
            return event.id
        event.status = "processing"
        event.error_message = ""
        event.save(update_fields=["status", "error_message"])
    try:
        payload = restore_telegram_event_payload(event.payload)
        get_adapter(event.integration).process_event(payload)
    except Exception as exc:
        event.status = "failed"
        event.error_message = f"{exc.__class__.__name__}: Telegram event processing failed"
        event.save(update_fields=["status", "error_message"])
        raise

    processed_at = timezone.now()
    event.status = "processed"
    event.processed_at = processed_at
    event.error_message = ""
    event.save(update_fields=["status", "processed_at", "error_message"])
    Integration.objects.filter(pk=event.integration_id).update(
        last_sync_at=processed_at,
        last_error="",
    )
    return event.id


def ingest_telegram_event(integration_id, payload):
    """Create one audit event and process it immediately for local reliability."""
    message_id = str(payload.get("message_id") or payload.get("id") or "")
    chat_id = str(payload.get("chat_id") or "")
    if not message_id or not chat_id:
        raise ValueError("Telegram payload has no message_id or chat_id")

    integration = Integration.objects.get(
        pk=integration_id,
        platform="telegram",
        status="active",
    )
    external_event_id = f"message:{chat_id}:{message_id}"
    stored = _stored_payload(payload)
    with transaction.atomic():
        event, created = IntegrationEvent.objects.get_or_create(
            integration=integration,
            external_event_id=external_event_id,
            defaults={
                "event_type": "message",
                "payload": stored,
            },
        )

    if event.status != "processed":
        process_stored_telegram_event(event)
    return event, created


class TelegramListenerSupervisor:
    def __init__(self, reconcile_interval=10, reconnect_delay=5, max_reconnect_delay=60):
        self.reconcile_interval = reconcile_interval
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self._tasks = {}
        self._stop_event = asyncio.Event()

    def request_stop(self):
        self._stop_event.set()

    async def run(self):
        logger.info("Telegram listener supervisor started")
        try:
            while not self._stop_event.is_set():
                await self._reconcile()
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.reconcile_interval,
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            await self._stop_all()
            logger.info("Telegram listener supervisor stopped")

    async def _active_integration_ids(self):
        queryset = Integration.objects.filter(
            platform="telegram",
            status="active",
        ).values_list("id", flat=True)
        return set(await sync_to_async(list, thread_sensitive=True)(queryset))

    async def _reconcile(self):
        active_ids = await self._active_integration_ids()
        for integration_id, task in list(self._tasks.items()):
            if task.done() or integration_id not in active_ids:
                if not task.done():
                    task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await task
                self._tasks.pop(integration_id, None)

        for integration_id in active_ids - self._tasks.keys():
            self._tasks[integration_id] = asyncio.create_task(
                self._run_integration(integration_id),
                name=f"telegram-integration-{integration_id}",
            )

    async def _get_active_integration(self, integration_id):
        return await Integration.objects.filter(
            pk=integration_id,
            platform="telegram",
            status="active",
        ).afirst()

    async def _run_integration(self, integration_id):
        delay = self.reconnect_delay
        while not self._stop_event.is_set():
            integration = await self._get_active_integration(integration_id)
            if integration is None:
                return
            session = integration.get_session()
            if not session:
                await self._mark_terminal_error(
                    integration_id,
                    "Telegram session is missing. Reconnect the integration.",
                )
                return

            adapter = get_adapter(integration)
            client = None
            try:
                from telethon import events

                client = adapter._client(session)

                async def on_new_message(event):
                    try:
                        payload = await normalize_telegram_event(event)
                        await sync_to_async(
                            ingest_telegram_event,
                            thread_sensitive=True,
                        )(integration_id, payload)
                    except Integration.DoesNotExist:
                        return
                    except Exception:
                        logger.exception(
                            "Telegram event processing failed for integration=%s",
                            integration_id,
                        )

                client.add_event_handler(on_new_message, events.NewMessage(incoming=True))
                await client.connect()
                if not await client.is_user_authorized():
                    await self._mark_terminal_error(
                        integration_id,
                        "Telegram authorization expired. Reconnect the integration.",
                    )
                    return

                await Integration.objects.filter(pk=integration_id).aupdate(
                    last_error="",
                    last_sync_at=timezone.now(),
                )
                delay = self.reconnect_delay
                await client.catch_up()
                await client.run_until_disconnected()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if exc.__class__.__name__ in TERMINAL_SESSION_ERRORS:
                    await self._mark_terminal_error(
                        integration_id,
                        "Telegram authorization expired. Reconnect the integration.",
                    )
                    return
                logger.warning(
                    "Telegram listener disconnected for integration=%s (%s)",
                    integration_id,
                    exc.__class__.__name__,
                )
                await Integration.objects.filter(pk=integration_id).aupdate(
                    last_error="Telegram listener is reconnecting.",
                )
            finally:
                if client is not None:
                    with suppress(Exception):
                        await client.disconnect()

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                delay = min(delay * 2, self.max_reconnect_delay)

    async def _mark_terminal_error(self, integration_id, message):
        await Integration.objects.filter(pk=integration_id).aupdate(
            status="error",
            last_error=message,
        )

    async def _stop_all(self):
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

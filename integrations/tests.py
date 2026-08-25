import hashlib
import hmac
import json
from datetime import datetime, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from asgiref.sync import async_to_sync
from contacts.models import Contact
from core.management.commands.runserver import (
    Command as CoreRunserverCommand,
    TelegramListenerThread,
)
from django.contrib.staticfiles.management.commands.runserver import (
    Command as StaticFilesRunserverCommand,
)
from django.core.cache import cache
from django.core.management import get_commands
from django.test import SimpleTestCase
from conversations.serializers import ConversationSerializer
from messages.serializers import MessageSerializer
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase, APITransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User

from audit.models import IntegrationEvent
from conversations.models import Conversation
from messages.models import Message
from notifications.models import Notification

from .models import Integration
from .processing import persist_incoming
from .security import decrypt_json
from .services.base import BaseIntegration
from .services.telegram_mtproto import TelegramMTProtoIntegration
from .telegram_runtime import (
    ingest_telegram_event,
    normalize_telegram_event,
    process_stored_telegram_event,
)


TELEGRAM_API_HASH = "0123456789abcdef0123456789abcdef"


class CredentialHolder:
    def __init__(self, credentials=None, pk=1):
        self.pk = pk
        self._credentials = credentials or {}

    def get_credentials(self):
        return self._credentials


class RunserverTelegramListenerTests(SimpleTestCase):
    def test_runserver_command_discovery_resolves_to_core(self):
        get_commands.cache_clear()
        try:
            self.assertEqual(get_commands()["runserver"], "core")
        finally:
            get_commands.cache_clear()

    def test_autoreloader_parent_does_not_start_listener(self):
        command = CoreRunserverCommand()

        with (
            patch(
                "django.core.management.commands.runserver.autoreload.run_with_reloader"
            ) as run_with_reloader,
            patch(
                "core.management.commands.runserver.TelegramListenerThread"
            ) as listener_class,
        ):
            command.run(use_reloader=True, use_telegram_listener=True)

        run_with_reloader.assert_called_once()
        self.assertEqual(run_with_reloader.call_args.args[0], command.inner_run)
        listener_class.assert_not_called()

    def test_on_bind_starts_listener_exactly_once(self):
        command = CoreRunserverCommand()
        command._use_telegram_listener = True
        listener = Mock()
        listener.is_alive = True

        with (
            patch.object(StaticFilesRunserverCommand, "on_bind") as parent_on_bind,
            patch(
                "core.management.commands.runserver.TelegramListenerThread",
                return_value=listener,
            ) as listener_class,
        ):
            command.on_bind("8000")
            command.on_bind("8000")

        self.assertEqual(parent_on_bind.call_count, 2)
        listener_class.assert_called_once_with()
        listener.start.assert_called_once_with()

    def test_on_bind_honors_no_telegram_listener_option(self):
        command = CoreRunserverCommand()
        command._use_telegram_listener = False

        with (
            patch.object(StaticFilesRunserverCommand, "on_bind") as parent_on_bind,
            patch(
                "core.management.commands.runserver.TelegramListenerThread"
            ) as listener_class,
        ):
            command.on_bind("8000")

        parent_on_bind.assert_called_once_with("8000")
        listener_class.assert_not_called()

    def test_no_reload_run_starts_on_bind_and_stops_on_shutdown(self):
        command = CoreRunserverCommand()
        listener = Mock()
        listener.is_alive = True

        def serve(**options):
            command.on_bind("8000")
            return "server-stopped"

        with (
            patch.object(StaticFilesRunserverCommand, "run", side_effect=serve),
            patch.object(StaticFilesRunserverCommand, "on_bind"),
            patch(
                "core.management.commands.runserver.TelegramListenerThread",
                return_value=listener,
            ),
        ):
            result = command.run(
                use_reloader=False,
                use_telegram_listener=True,
            )

        self.assertEqual(result, "server-stopped")
        listener.start.assert_called_once_with()
        listener.stop.assert_called_once_with()

    def test_run_exception_still_stops_started_listener(self):
        command = CoreRunserverCommand()
        listener = Mock()
        listener.is_alive = True

        def serve(**options):
            command.on_bind("8000")
            raise RuntimeError("server stopped unexpectedly")

        with (
            patch.object(StaticFilesRunserverCommand, "run", side_effect=serve),
            patch.object(StaticFilesRunserverCommand, "on_bind"),
            patch(
                "core.management.commands.runserver.TelegramListenerThread",
                return_value=listener,
            ),
            self.assertRaisesRegex(RuntimeError, "server stopped unexpectedly"),
        ):
            command.run(use_reloader=False, use_telegram_listener=True)

        listener.start.assert_called_once_with()
        listener.stop.assert_called_once_with()

    def test_listener_stop_requests_supervisor_and_uses_bounded_join(self):
        listener = TelegramListenerThread()
        thread = Mock()
        thread.is_alive.return_value = True
        loop = Mock()
        supervisor = Mock()
        listener._thread = thread
        listener._loop = loop
        listener._supervisor = supervisor

        listener.stop(timeout=2.5)

        self.assertTrue(listener._stop_requested.is_set())
        loop.call_soon_threadsafe.assert_called_once_with(
            supervisor.request_stop
        )
        thread.join.assert_called_once_with(timeout=2.5)


class TelegramClientTests(SimpleTestCase):
    def tearDown(self):
        cache.clear()

    def test_client_requires_per_integration_credentials(self):
        adapter = TelegramMTProtoIntegration(CredentialHolder())

        with self.assertRaises(ValidationError) as error:
            adapter._client()

        self.assertIn("API ID", str(error.exception))
        self.assertIn("API Hash", str(error.exception))

    @patch("telethon.TelegramClient")
    def test_clients_use_their_own_integration_credentials(self, telegram_client):
        first = TelegramMTProtoIntegration(
            CredentialHolder({"api_id": 111111, "api_hash": "a" * 32}, pk=1)
        )
        second = TelegramMTProtoIntegration(
            CredentialHolder({"api_id": 222222, "api_hash": "b" * 32}, pk=2)
        )

        first._client()
        second._client()

        first_args = telegram_client.call_args_list[0].args
        second_args = telegram_client.call_args_list[1].args
        self.assertEqual(first_args[1:], (111111, "a" * 32))
        self.assertEqual(second_args[1:], (222222, "b" * 32))

    def test_pending_auth_cache_is_encrypted(self):
        holder = CredentialHolder(
            {"api_id": 111111, "api_hash": TELEGRAM_API_HASH},
            pk=91,
        )
        adapter = TelegramMTProtoIntegration(holder)
        client = SimpleNamespace(
            connect=AsyncMock(),
            disconnect=AsyncMock(),
            send_code_request=AsyncMock(
                return_value=SimpleNamespace(phone_code_hash="phone-code-hash")
            ),
            session=SimpleNamespace(save=Mock(return_value="telegram-session-secret")),
        )

        with patch.object(adapter, "_client", return_value=client):
            async_to_sync(adapter.start)("+992900001122")

        cached = cache.get("tg_auth:91")
        self.assertIsInstance(cached, str)
        self.assertNotIn("telegram-session-secret", cached)
        self.assertNotIn("+992900001122", cached)
        self.assertEqual(
            decrypt_json(cached),
            {
                "phone": "+992900001122",
                "hash": "phone-code-hash",
                "session": "telegram-session-secret",
            },
        )
        client.disconnect.assert_awaited_once()


class Telegram2FAAsyncActivationTests(APITransactionTestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="two-factor-owner@example.com",
            username="two-factor-owner",
            password="StrongPass123!",
        )
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_telegram_2fa_activation_persists_from_async_flow(self):
        integration = Integration(
            user=self.user,
            platform="telegram",
            name="Telegram with 2FA",
            status="pending",
        )
        integration.set_credentials(
            {"api_id": 123456, "api_hash": TELEGRAM_API_HASH}
        )
        integration.save()
        async_to_sync(TelegramMTProtoIntegration(integration)._save_auth)(
            {
                "phone": "+992900001122",
                "hash": "phone-code-hash",
                "session": "pending-telegram-session",
            }
        )
        telegram_client = SimpleNamespace(
            connect=AsyncMock(),
            disconnect=AsyncMock(),
            sign_in=AsyncMock(),
            get_me=AsyncMock(return_value=SimpleNamespace(id=778899)),
            session=SimpleNamespace(
                save=Mock(return_value="authorized-telegram-session")
            ),
        )

        with patch.object(
            TelegramMTProtoIntegration,
            "_client",
            return_value=telegram_client,
        ):
            response = self.client.post(
                "/api/integrations/telegram/connect/2fa/",
                {
                    "integration_id": integration.pk,
                    "password": "telegram-2fa-password",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        integration.refresh_from_db()
        self.assertEqual(integration.status, "active")
        self.assertEqual(integration.external_account_id, "778899")
        self.assertEqual(integration.get_session(), "authorized-telegram-session")
        self.assertIsNone(cache.get(f"tg_auth:{integration.pk}"))
        self.assertNotIn("credentials", response.data)
        self.assertNotIn("session_data", response.data)
        self.assertNotIn("telegram-2fa-password", json.dumps(response.data))
        telegram_client.sign_in.assert_awaited_once_with(
            password="telegram-2fa-password"
        )
        telegram_client.disconnect.assert_awaited_once()


class TelegramRuntimeNormalizationTests(SimpleTestCase):
    def test_normalizes_json_safe_incoming_event_with_private_peer(self):
        peer = type(
            "InputPeerUser",
            (),
            {"user_id": 440011, "access_hash": 998877665544332211},
        )()
        sender = SimpleNamespace(
            first_name="Munis",
            last_name="Customer",
            username="munis_customer",
            phone="992900001122",
        )
        event = SimpleNamespace(
            id=77,
            chat_id=440011,
            sender_id=440011,
            raw_text="Салом",
            date=datetime(2026, 8, 22, 8, 30, tzinfo=dt_timezone.utc),
            message=SimpleNamespace(
                id=77,
                raw_text="Салом",
                sticker=None,
                video=None,
                voice=None,
                audio=None,
                photo=None,
                document=None,
                geo=None,
            ),
            get_sender=AsyncMock(return_value=sender),
            get_chat=AsyncMock(
                return_value=SimpleNamespace(
                    title="Customer support chat",
                    first_name="",
                    last_name="",
                )
            ),
            get_input_chat=AsyncMock(return_value=peer),
        )

        payload = async_to_sync(normalize_telegram_event)(event)

        self.assertEqual(payload["message_id"], "77")
        self.assertEqual(payload["chat_id"], "440011")
        self.assertEqual(payload["sender_type"], "customer")
        self.assertEqual(payload["type"], "text")
        self.assertEqual(payload["text"], "Салом")
        self.assertEqual(payload["chat_name"], "Customer support chat")
        self.assertEqual(
            payload["_telegram_peer"],
            {
                "type": "user",
                "id": 440011,
                "access_hash": 998877665544332211,
            },
        )
        json.dumps(payload)


class TelegramRuntimeIngestTests(APITransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="listener-owner@example.com",
            username="listener-owner",
            password="StrongPass123!",
        )
        self.integration = Integration.objects.create(
            user=self.user,
            platform="telegram",
            name="Listener Telegram",
            status="active",
        )

    def test_ingest_is_idempotent_and_never_persists_raw_access_hash(self):
        access_hash = 998877665544332211
        payload = {
            "id": "91",
            "message_id": "91",
            "chat_id": "440011",
            "contact_id": "440011",
            "from": "440011",
            "sender_type": "customer",
            "name": "Telegram Customer",
            "username": "telegram_customer",
            "phone": "",
            "type": "text",
            "text": "Incoming Telegram message",
            "timestamp": "2026-08-22T08:30:00+00:00",
            "_telegram_peer": {
                "type": "user",
                "id": 440011,
                "access_hash": access_hash,
            },
        }

        first, first_created = ingest_telegram_event(self.integration.pk, payload)
        second, second_created = ingest_telegram_event(self.integration.pk, payload)

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(IntegrationEvent.objects.count(), 1)
        first.refresh_from_db()
        self.assertEqual(first.status, "processed")
        self.assertIn("_telegram_peer_encrypted", first.payload)
        self.assertNotIn("_telegram_peer", first.payload)
        self.assertNotIn(str(access_hash), json.dumps(first.payload))

        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)
        message = Message.objects.get()
        self.assertNotIn("_telegram_peer", message.metadata)
        self.assertNotIn(str(access_hash), json.dumps(message.metadata))

        conversation = Conversation.objects.get()
        self.assertNotIn(str(access_hash), conversation.external_peer_data)
        self.assertEqual(
            conversation.get_external_peer(),
            {
                "type": "user",
                "id": 440011,
                "access_hash": access_hash,
            },
        )

    def test_processing_event_is_not_processed_twice(self):
        event = IntegrationEvent.objects.create(
            integration=self.integration,
            event_type="message",
            external_event_id="message:440011:92",
            status="processing",
            payload={
                "id": "92",
                "message_id": "92",
                "chat_id": "440011",
                "contact_id": "440011",
                "type": "text",
                "text": "Already being processed",
            },
        )

        process_stored_telegram_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, "processing")
        self.assertEqual(Message.objects.count(), 0)

    def test_persist_incoming_encrypts_peer_and_serializers_never_expose_it(self):
        peer = {
            "type": "user",
            "id": 551122,
            "access_hash": "peer-access-hash-secret",
        }

        message, created = persist_incoming(
            self.integration,
            {
                "id": "peer-message-1",
                "chat_id": "peer-chat-1",
                "contact_id": "peer-contact-1",
                "name": "Private Peer Customer",
                "type": "text",
                "text": "Private peer persistence",
                "_telegram_peer": peer,
            },
        )

        self.assertTrue(created)
        conversation = message.conversation
        self.assertTrue(conversation.external_peer_data.startswith("fernet:"))
        self.assertNotIn("peer-access-hash-secret", conversation.external_peer_data)
        self.assertEqual(conversation.get_external_peer(), peer)
        self.assertNotIn("_telegram_peer", message.metadata)

        message_data = MessageSerializer(message).data
        conversation_data = ConversationSerializer(conversation).data
        serialized = json.dumps(
            {"message": message_data, "conversation": conversation_data}
        )
        self.assertNotIn("external_peer_data", conversation_data)
        self.assertNotIn("_telegram_peer", serialized)
        self.assertNotIn("peer-access-hash-secret", serialized)


class SharedMessagePersistenceTests(APITransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="instagram-owner@example.com",
            username="instagram-owner",
            password="StrongPass123!",
        )
        self.integration = Integration.objects.create(
            user=self.user,
            platform="instagram",
            name="Instagram account",
            status="active",
            external_account_id="ig-business-1001",
        )

    def payload(self, message_id, timestamp, **overrides):
        data = {
            "id": message_id,
            "message_id": message_id,
            "chat_id": "ig-customer-2002",
            "contact_id": "ig-customer-2002",
            "from": "ig-customer-2002",
            "sender_type": "customer",
            "name": "Instagram Customer",
            "username": "ig_customer",
            "type": "text",
            "text": f"message {message_id}",
            "timestamp": timestamp,
        }
        data.update(overrides)
        return data

    def test_only_new_customer_messages_notify_and_broadcast(self):
        with patch("integrations.processing._broadcast_new_message") as broadcast:
            customer, customer_created = persist_incoming(
                self.integration,
                self.payload("ig-mid-customer", "2026-08-22T10:00:00+00:00"),
            )
            duplicate, duplicate_created = persist_incoming(
                self.integration,
                self.payload("ig-mid-customer", "2026-08-22T10:00:00+00:00"),
            )
            business, business_created = persist_incoming(
                self.integration,
                self.payload(
                    "ig-mid-business",
                    "2026-08-22T10:01:00+00:00",
                    sender_type="business",
                    text="Business echo",
                ),
            )

        self.assertTrue(customer_created)
        self.assertFalse(duplicate_created)
        self.assertEqual(customer.pk, duplicate.pk)
        self.assertTrue(business_created)
        self.assertEqual(business.sender_type, "business")
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.get()
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.message, customer.text)
        broadcast.assert_called_once_with(
            self.user.pk,
            customer.pk,
            customer.conversation_id,
            "instagram",
        )

    def test_late_event_does_not_move_last_message_at_backwards(self):
        newest = datetime(2026, 8, 22, 12, 30, tzinfo=dt_timezone.utc)
        older = datetime(2026, 8, 22, 9, 15, tzinfo=dt_timezone.utc)

        first, _ = persist_incoming(
            self.integration,
            self.payload("ig-mid-newest", newest.isoformat()),
        )
        persist_incoming(
            self.integration,
            self.payload("ig-mid-late", older.isoformat()),
        )

        conversation = Conversation.objects.get(pk=first.conversation_id)
        self.assertEqual(conversation.last_message_at, newest)
        self.assertEqual(conversation.messages.count(), 2)

    def test_echo_created_before_send_result_is_reused_as_outgoing(self):
        echo_at = datetime(2026, 8, 22, 10, 0, tzinfo=dt_timezone.utc)
        sent_at = datetime(2026, 8, 22, 10, 1, tzinfo=dt_timezone.utc)
        echo, echo_created = persist_incoming(
            self.integration,
            self.payload(
                "ig-mid-echo-first",
                echo_at.isoformat(),
                sender_type="business",
                text="Webhook echo",
            ),
        )

        outgoing = BaseIntegration(self.integration).save_outgoing(
            echo.conversation,
            "Reply sent from the hub",
            external_id="ig-mid-echo-first",
            external_created_at=sent_at,
            metadata={"delivery_status": "sent"},
        )

        self.assertTrue(echo_created)
        self.assertEqual(outgoing.pk, echo.pk)
        self.assertEqual(Message.objects.count(), 1)
        outgoing.refresh_from_db()
        self.assertEqual(outgoing.sender_type, "business")
        self.assertEqual(outgoing.text, "Reply sent from the hub")
        self.assertEqual(outgoing.external_created_at, sent_at)
        self.assertEqual(outgoing.metadata, {"delivery_status": "sent"})
        self.assertEqual(Notification.objects.count(), 0)
        outgoing.conversation.refresh_from_db()
        self.assertEqual(outgoing.conversation.last_message_at, sent_at)

    def test_echo_received_after_saved_outgoing_does_not_duplicate_message(self):
        contact = Contact.objects.create(
            integration=self.integration,
            external_id="ig-customer-after",
            name="Echo Customer",
        )
        conversation = Conversation.objects.create(
            integration=self.integration,
            contact=contact,
            external_chat_id="ig-customer-after",
        )
        sent_at = datetime(2026, 8, 22, 11, 0, tzinfo=dt_timezone.utc)
        outgoing = BaseIntegration(self.integration).save_outgoing(
            conversation,
            "Already saved reply",
            external_id="ig-mid-send-first",
            external_created_at=sent_at,
            metadata={"delivery_status": "sent"},
        )

        echoed, created = persist_incoming(
            self.integration,
            self.payload(
                "ig-mid-send-first",
                sent_at.isoformat(),
                chat_id="ig-customer-after",
                contact_id="ig-customer-after",
                sender_type="business",
                text="Already saved reply",
            ),
        )

        self.assertFalse(created)
        self.assertEqual(echoed.pk, outgoing.pk)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 0)
        outgoing.refresh_from_db()
        self.assertEqual(outgoing.metadata, {"delivery_status": "sent"})


class TelegramMessageDeliveryAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="sender@example.com",
            username="sender",
            password="StrongPass123!",
        )
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.integration = Integration(
            user=self.user,
            platform="telegram",
            name="Delivery account",
            status="active",
        )
        self.integration.set_credentials(
            {"api_id": 123456, "api_hash": TELEGRAM_API_HASH}
        )
        self.integration.set_session("authorized-session-secret")
        self.integration.save()
        self.contact = Contact.objects.create(
            integration=self.integration,
            external_id="telegram-user-7788",
            name="Reply Customer",
            username="reply_customer",
        )
        self.conversation = Conversation.objects.create(
            integration=self.integration,
            contact=self.contact,
            external_chat_id="-100778899",
            title="Reply chat",
        )
        self.peer = {
            "type": "user",
            "id": 7788,
            "access_hash": 998877665544332211,
        }
        self.conversation.set_external_peer(self.peer)
        self.conversation.save(update_fields=["external_peer_data", "updated_at"])

    def test_send_api_uses_decrypted_peer_and_session_and_stores_sent_message(self):
        sent_at = datetime(2026, 8, 22, 7, 45, tzinfo=dt_timezone.utc)
        telegram_result = SimpleNamespace(id=556677, date=sent_at)

        with patch.object(
            TelegramMTProtoIntegration,
            "_send_to_telegram",
            new_callable=AsyncMock,
            return_value=telegram_result,
        ) as send_to_telegram:
            response = self.client.post(
                f"/api/conversations/{self.conversation.pk}/messages/",
                {"text": "Reply delivered to Telegram"},
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        message = Message.objects.get(
            conversation=self.conversation,
            external_message_id="556677",
        )
        self.assertEqual(message.sender_type, "business")
        self.assertEqual(message.text, "Reply delivered to Telegram")
        self.assertEqual(message.external_created_at, sent_at)
        self.assertEqual(message.metadata, {"delivery_status": "sent"})
        send_to_telegram.assert_awaited_once_with(
            session="authorized-session-secret",
            peer=self.peer,
            fallback_chat_id="-100778899",
            fallback_username="reply_customer",
            text="Reply delivered to Telegram",
        )
        serialized = json.dumps(response.data)
        self.assertNotIn("authorized-session-secret", serialized)
        self.assertNotIn(str(self.peer["access_hash"]), serialized)
        self.assertNotIn("external_peer_data", response.data)

    def test_send_api_failure_creates_no_sent_row_and_returns_sanitized_error(self):
        transport_error = (
            "transport failed with authorized-session-secret and "
            f"{TELEGRAM_API_HASH}"
        )

        with patch.object(
            TelegramMTProtoIntegration,
            "_send_to_telegram",
            new_callable=AsyncMock,
            side_effect=RuntimeError(transport_error),
        ) as send_to_telegram:
            response = self.client.post(
                f"/api/conversations/{self.conversation.pk}/messages/",
                {"text": "This reply must not be marked sent"},
                format="json",
            )

        self.assertEqual(response.status_code, 500)
        self.assertFalse(
            Message.objects.filter(
                conversation=self.conversation,
                sender_type="business",
            ).exists()
        )
        serialized = json.dumps(response.data)
        self.assertNotIn(transport_error, serialized)
        self.assertNotIn("authorized-session-secret", serialized)
        self.assertNotIn(TELEGRAM_API_HASH, serialized)
        self.assertIn("Telegram", serialized)
        send_to_telegram.assert_awaited_once()


class IntegrationCredentialAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="owner@example.com",
            username="owner",
            password="StrongPass123!",
        )
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def telegram_payload(self, **overrides):
        payload = {
            "name": "Owner Telegram",
            "phone": "+992900001122",
            "api_id": 123456,
            "api_hash": TELEGRAM_API_HASH,
        }
        payload.update(overrides)
        return payload

    def test_telegram_start_encrypts_credentials_and_never_returns_them(self):
        adapter = Mock()
        adapter.start = AsyncMock()

        with patch("integrations.views.get_adapter", return_value=adapter):
            response = self.client.post(
                "/api/integrations/telegram/connect/start/",
                self.telegram_payload(),
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.data), {"integration_id", "status"})
        integration = Integration.objects.get(pk=response.data["integration_id"])
        raw_credentials = str(integration.credentials)
        self.assertNotIn(TELEGRAM_API_HASH, raw_credentials)
        self.assertNotIn("123456", raw_credentials)
        self.assertTrue(integration.credentials["encrypted"].startswith("fernet:"))
        self.assertEqual(
            integration.get_credentials(),
            {"api_id": 123456, "api_hash": TELEGRAM_API_HASH},
        )
        adapter.start.assert_awaited_once_with("+992900001122")

        listed = self.client.get("/api/integrations/").data["results"][0]
        serialized = json.dumps(listed)
        self.assertNotIn("credentials", listed)
        self.assertNotIn("session_data", listed)
        self.assertNotIn("api_hash", serialized.lower())
        self.assertNotIn(TELEGRAM_API_HASH, serialized)

    def test_telegram_start_validates_credentials_before_creating_row(self):
        missing = self.client.post(
            "/api/integrations/telegram/connect/start/",
            self.telegram_payload(api_hash=None),
            format="json",
        )
        invalid = self.client.post(
            "/api/integrations/telegram/connect/start/",
            self.telegram_payload(api_hash="not-a-valid-hash"),
            format="json",
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(Integration.objects.count(), 0)

    def test_failed_telegram_start_removes_encrypted_pending_row(self):
        adapter = Mock()
        adapter.start = AsyncMock(side_effect=ValidationError("Telegram unavailable"))

        with patch("integrations.views.get_adapter", return_value=adapter):
            response = self.client.post(
                "/api/integrations/telegram/connect/start/",
                self.telegram_payload(),
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Integration.objects.count(), 0)

    def test_generic_patch_cannot_overwrite_secret_fields(self):
        integration = Integration(
            user=self.user,
            platform="telegram",
            name="Original",
        )
        integration.set_credentials({"api_id": 1, "api_hash": TELEGRAM_API_HASH})
        integration.set_session("original-session")
        integration.save()

        response = self.client.patch(
            f"/api/integrations/{integration.pk}/",
            {
                "name": "Renamed",
                "credentials": {"api_hash": "exposed"},
                "session_data": "exposed",
                "webhook_url": "https://attacker.example/webhook",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        integration.refresh_from_db()
        self.assertEqual(integration.name, "Renamed")
        self.assertEqual(integration.get_credentials()["api_hash"], TELEGRAM_API_HASH)
        self.assertEqual(integration.get_session(), "original-session")
        self.assertEqual(integration.webhook_url, "")
        self.assertNotIn("credentials", response.data)
        self.assertNotIn("session_data", response.data)

    def test_other_user_cannot_verify_an_integration(self):
        other = User.objects.create_user(
            email="other@example.com",
            username="other",
            password="StrongPass123!",
        )
        integration = Integration.objects.create(
            user=other,
            platform="telegram",
            name="Other Telegram",
            status="pending",
        )

        response = self.client.post(
            "/api/integrations/telegram/connect/verify/",
            {"integration_id": integration.pk, "code": "12345"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def whatsapp_payload(self, **overrides):
        payload = {
            "name": "Owner WhatsApp",
            "phone_number_id": "123456789012345",
            "business_account_id": "987654321098765",
            "access_token": "access-token-secret",
            "app_secret": "app-secret-value",
            "verify_token": "verify-token-value",
        }
        payload.update(overrides)
        return payload

    def create_whatsapp_integration(self):
        response = self.client.post(
            "/api/integrations/whatsapp/connect/",
            self.whatsapp_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response, Integration.objects.get(pk=response.data["id"])

    def test_whatsapp_credentials_are_encrypted_and_callback_is_per_integration(self):
        response, integration = self.create_whatsapp_integration()

        serialized = json.dumps(response.data)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("app_secret", serialized)
        self.assertNotIn("verify_token", serialized)
        self.assertNotIn("access-token-secret", str(integration.credentials))
        self.assertEqual(
            integration.get_credentials()["app_secret"],
            "app-secret-value",
        )
        self.assertTrue(
            response.data["webhook_url"].endswith(
                f"/api/webhooks/whatsapp/{integration.pk}/"
            )
        )

        verified = self.client.get(
            f"/api/webhooks/whatsapp/{integration.pk}/",
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-token-value",
                "hub.challenge": "24680",
            },
        )
        rejected = self.client.get(
            f"/api/webhooks/whatsapp/{integration.pk}/",
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "24680",
            },
        )
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.content, b"24680")
        self.assertEqual(rejected.status_code, 403)

    def test_whatsapp_webhook_uses_only_its_integrations_app_secret(self):
        _, integration = self.create_whatsapp_integration()
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {
                                    "phone_number_id": integration.external_account_id
                                },
                                "messages": [
                                    {
                                        "id": "wamid-owner-1",
                                        "from": "992900001100",
                                        "text": {"body": "hello"},
                                        "type": "text",
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        valid_signature = "sha256=" + hmac.new(
            b"app-secret-value", body, hashlib.sha256
        ).hexdigest()
        wrong_signature = "sha256=" + hmac.new(
            b"another-users-secret", body, hashlib.sha256
        ).hexdigest()
        url = f"/api/webhooks/whatsapp/{integration.pk}/"

        rejected = self.client.generic(
            "POST",
            url,
            body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=wrong_signature,
        )
        self.assertEqual(rejected.status_code, 403)

        accepted = self.client.generic(
            "POST",
            url,
            body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=valid_signature,
        )

        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data, {"accepted": 1})

        # The webhook persists the message synchronously, so it must already
        # be in the database right after the webhook call.
        event = IntegrationEvent.objects.filter(
            integration=integration,
            external_event_id="wamid-owner-1",
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.status, "processed")
        self.assertTrue(
            Message.objects.filter(
                conversation__integration=integration,
                text="hello",
            ).exists()
        )

    def test_whatsapp_interactive_message_without_timestamp_is_persisted(self):
        _, integration = self.create_whatsapp_integration()
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": integration.external_account_id},
                        "contacts": [{"profile": {"name": "Customer"}}],
                        "messages": [{
                            "id": "wamid-interactive-1",
                            "from": "992900001100",
                            "type": "interactive",
                            "interactive": {
                                "type": "button_reply",
                                "button_reply": {"title": "Order now", "id": "order-now"},
                            },
                        }],
                    }
                }]
            }]
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        signature = "sha256=" + hmac.new(
            b"app-secret-value", body, hashlib.sha256
        ).hexdigest()
        response = self.client.generic(
            "POST",
            f"/api/webhooks/whatsapp/{integration.pk}/",
            body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Message.objects.filter(
                conversation__integration=integration,
                text="Order now",
            ).exists()
        )

    def test_viber_message_webhook_is_persisted(self):
        response = self.client.post(
            "/api/integrations/viber/connect/",
            {"name": "Owner Viber", "auth_token": "viber-auth-token-123456"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        integration = Integration.objects.get(pk=response.data["id"])
        payload = {"event": "message", "timestamp": 1710000000000, "message_token": 77, "sender": {"id": "viber-user", "name": "Viber User"}, "message": {"type": "text", "text": "Hello from Viber"}}
        body = json.dumps(payload, separators=(",", ":")).encode()
        signature = hmac.new(b"viber-auth-token-123456", body, hashlib.sha256).hexdigest()
        result = self.client.generic("POST", f"/api/webhooks/viber/{integration.pk}/", body, content_type="application/json", HTTP_X_VIBER_CONTENT_SIGNATURE=signature)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(Message.objects.filter(conversation__integration=integration, text="Hello from Viber").exists())

    def test_vk_confirmation_and_message_webhook_are_supported(self):
        response = self.client.post(
            "/api/integrations/vk/connect/",
            {"name": "Owner VK", "group_id": "123456", "access_token": "vk-access-token-123456", "secret": "vk-secret", "confirmation": "vk-confirm", "api_version": "5.199"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        integration = Integration.objects.get(pk=response.data["id"])
        confirmed = self.client.post(f"/api/webhooks/vk/{integration.pk}/", {"type": "confirmation"}, format="json")
        self.assertEqual(confirmed.content, b"vk-confirm")
        result = self.client.post(f"/api/webhooks/vk/{integration.pk}/", {"type": "message_new", "secret": "vk-secret", "object": {"id": 88, "from_id": 42, "peer_id": 42, "date": 1710000000, "text": "Hello from VK"}}, format="json")
        self.assertEqual(result.content, b"ok")
        self.assertTrue(Message.objects.filter(conversation__integration=integration, text="Hello from VK").exists())

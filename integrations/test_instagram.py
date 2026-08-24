import hashlib
import hmac
import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from audit.models import IntegrationEvent
from contacts.models import Contact
from conversations.models import Conversation
from messages.models import Message
from notifications.models import Notification
from users.models import User

from .models import Integration
from .services.instagram_api import InstagramAPIClient
from .tasks import process_instagram_event, retry_failed_event
from .views import (
    INSTAGRAM_OAUTH_STATE_SALT,
    _instagram_browser_cookie_name,
)


INSTAGRAM_SETTINGS = {
    "INSTAGRAM_APP_ID": "1234567890",
    "INSTAGRAM_APP_SECRET": "instagram-app-secret",
    "INSTAGRAM_VERIFY_TOKEN": "instagram-verify-token",
    "INSTAGRAM_API_VERSION": "v24.0",
    "INSTAGRAM_REDIRECT_URI": (
        "https://hub.example/api/integrations/instagram/connect/callback/"
    ),
    "INSTAGRAM_OAUTH_STATE_TTL": 600,
    "CELERY_TASK_ALWAYS_EAGER": False,
}


@override_settings(**INSTAGRAM_SETTINGS)
class InstagramOAuthAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="instagram-owner@example.com",
            username="instagram-owner",
            password="StrongPass123!",
        )
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def tearDown(self):
        cache.clear()

    def start_oauth(self):
        response = self.client.post(
            "/api/integrations/instagram/connect/start/",
            {"name": "Owner Instagram"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        query = parse_qs(urlparse(response.data["authorization_url"]).query)
        return response, query["state"][0], query

    def test_start_uses_exact_redirect_and_returns_signed_short_lived_state(self):
        response, state, query = self.start_oauth()

        self.assertEqual(response.data["expires_in"], 600)
        self.assertEqual(
            query["redirect_uri"],
            [INSTAGRAM_SETTINGS["INSTAGRAM_REDIRECT_URI"]],
        )
        decoded = signing.loads(
            state,
            salt=INSTAGRAM_OAUTH_STATE_SALT,
            max_age=600,
        )
        self.assertEqual(decoded["user_id"], self.user.pk)
        self.assertEqual(decoded["name"], "Owner Instagram")
        self.assertTrue(decoded["nonce"])
        cookie = response.cookies[_instagram_browser_cookie_name(state)]
        self.assertEqual(cookie["max-age"], 600)
        self.assertEqual(
            cookie["path"],
            "/api/integrations/instagram/connect/callback/",
        )
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(bool(cookie["secure"]), not settings.DEBUG)

    def test_callback_encrypts_token_subscribes_and_state_cannot_be_replayed(self):
        _, state, _ = self.start_oauth()
        token_data = {
            "access_token": "per-user-instagram-access-token",
            "user_id": "17841400000000123",
            "expires_in": 5_184_000,
        }

        with (
            patch.object(
                InstagramAPIClient,
                "exchange_code",
                return_value=token_data,
            ) as exchange,
            patch.object(
                InstagramAPIClient,
                "get_own_profile",
                return_value={
                    "user_id": "17841400000000123",
                    "username": "owner_business",
                },
            ),
            patch.object(
                InstagramAPIClient,
                "subscribe_webhooks",
                return_value={"success": True},
            ) as subscribe,
        ):
            connected = self.client.get(
                "/api/integrations/instagram/connect/callback/",
                {"code": "oauth-code", "state": state},
            )
            replayed = self.client.get(
                "/api/integrations/instagram/connect/callback/",
                {"code": "oauth-code", "state": state},
            )

        self.assertEqual(connected.status_code, 302)
        self.assertEqual(connected["Location"], "/integrations?instagram=connected")
        cleared_cookie = connected.cookies[_instagram_browser_cookie_name(state)]
        self.assertEqual(cleared_cookie["max-age"], 0)
        self.assertEqual(
            cleared_cookie["path"],
            "/api/integrations/instagram/connect/callback/",
        )
        self.assertEqual(replayed.status_code, 302)
        self.assertEqual(replayed["Location"], "/integrations?instagram=error")
        exchange.assert_called_once_with(
            code="oauth-code",
            redirect_uri=INSTAGRAM_SETTINGS["INSTAGRAM_REDIRECT_URI"],
        )
        subscribe.assert_called_once_with(
            account_id="17841400000000123",
            access_token="per-user-instagram-access-token",
        )

        integration = Integration.objects.get(platform="instagram")
        self.assertEqual(integration.user, self.user)
        self.assertEqual(integration.status, "active")
        self.assertEqual(integration.external_account_id, "17841400000000123")
        self.assertNotIn(
            "per-user-instagram-access-token",
            json.dumps(integration.credentials),
        )
        self.assertTrue(integration.credentials["encrypted"].startswith("fernet:"))
        self.assertEqual(
            integration.get_credentials()["access_token"],
            "per-user-instagram-access-token",
        )
        listed = self.client.get("/api/integrations/").data["results"][0]
        self.assertNotIn("credentials", listed)
        self.assertNotIn("access_token", json.dumps(listed).lower())

    def test_forwarded_callback_without_browser_cookie_cannot_exchange_token(self):
        _, state, _ = self.start_oauth()
        cookie_name = _instagram_browser_cookie_name(state)
        forwarded_browser = APIClient()

        with (
            patch.object(
                InstagramAPIClient,
                "exchange_code",
                return_value={
                    "access_token": "browser-bound-token",
                    "user_id": "17841400000000125",
                    "expires_in": 5_184_000,
                },
            ) as exchange,
            patch.object(
                InstagramAPIClient,
                "get_own_profile",
                return_value={
                    "user_id": "17841400000000125",
                    "username": "browser_bound",
                },
            ),
            patch.object(
                InstagramAPIClient,
                "subscribe_webhooks",
                return_value={"success": True},
            ),
        ):
            rejected = forwarded_browser.get(
                "/api/integrations/instagram/connect/callback/",
                {"code": "forwarded-code", "state": state},
            )
            exchange.assert_not_called()
            self.assertFalse(
                Integration.objects.filter(platform="instagram").exists()
            )

            accepted = self.client.get(
                "/api/integrations/instagram/connect/callback/",
                {"code": "original-browser-code", "state": state},
            )

        self.assertEqual(rejected.status_code, 302)
        self.assertEqual(rejected["Location"], "/integrations?instagram=error")
        self.assertIn(cookie_name, rejected.cookies)
        self.assertEqual(rejected.cookies[cookie_name]["max-age"], 0)
        self.assertEqual(accepted["Location"], "/integrations?instagram=connected")
        exchange.assert_called_once_with(
            code="original-browser-code",
            redirect_uri=INSTAGRAM_SETTINGS["INSTAGRAM_REDIRECT_URI"],
        )
        self.assertEqual(
            Integration.objects.get(platform="instagram").get_credentials()[
                "access_token"
            ],
            "browser-bound-token",
        )

    def test_parallel_starts_use_independent_browser_cookies(self):
        first_response, first_state, _ = self.start_oauth()
        second_response, second_state, _ = self.start_oauth()
        first_name = _instagram_browser_cookie_name(first_state)
        second_name = _instagram_browser_cookie_name(second_state)

        self.assertNotEqual(first_name, second_name)
        self.assertIn(first_name, first_response.cookies)
        self.assertIn(second_name, second_response.cookies)
        self.assertIn(first_name, self.client.cookies)
        self.assertIn(second_name, self.client.cookies)

    def test_denied_callback_consumes_state_and_redirects_without_creating_row(self):
        _, state, _ = self.start_oauth()

        denied = self.client.get(
            "/api/integrations/instagram/connect/callback/",
            {"error": "access_denied", "state": state},
        )
        replayed = self.client.get(
            "/api/integrations/instagram/connect/callback/",
            {"code": "later-code", "state": state},
        )

        self.assertEqual(denied["Location"], "/integrations?instagram=error")
        self.assertEqual(replayed["Location"], "/integrations?instagram=error")
        self.assertFalse(Integration.objects.filter(platform="instagram").exists())

    @override_settings(DEBUG=False, INSTAGRAM_REDIRECT_URI="")
    def test_production_start_requires_fixed_redirect_uri(self):
        response = self.client.post(
            "/api/integrations/instagram/connect/start/",
            {"name": "Instagram"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Integration.objects.filter(platform="instagram").exists())

    @override_settings(INSTAGRAM_VERIFY_TOKEN="")
    def test_start_requires_global_webhook_verify_token(self):
        response = self.client.post(
            "/api/integrations/instagram/connect/start/",
            {"name": "Instagram"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Integration.objects.filter(platform="instagram").exists())

    def test_disconnect_unsubscribes_and_erases_per_user_token(self):
        integration = Integration(
            user=self.user,
            platform="instagram",
            name="Owner Instagram",
            status="active",
            external_account_id="17841400000000124",
            webhook_url="https://hub.example/api/webhooks/instagram/",
        )
        integration.set_credentials({"access_token": "disconnect-token"})
        integration.save()

        with patch.object(
            InstagramAPIClient,
            "unsubscribe_webhooks",
            return_value={"success": True},
        ) as unsubscribe:
            response = self.client.post(
                "/api/integrations/instagram/disconnect/",
                {"integration_id": integration.pk},
                format="json",
            )

        self.assertEqual(response.status_code, 204)
        unsubscribe.assert_called_once_with(
            account_id="17841400000000124",
            access_token="disconnect-token",
        )
        integration.refresh_from_db()
        self.assertEqual(integration.status, "inactive")
        self.assertEqual(integration.get_credentials(), {})
        self.assertEqual(integration.credentials, {})
        self.assertEqual(integration.webhook_url, "")


@override_settings(**INSTAGRAM_SETTINGS)
class InstagramWebhookTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="instagram-webhook@example.com",
            username="instagram-webhook",
            password="StrongPass123!",
        )
        self.integration = Integration(
            user=self.user,
            platform="instagram",
            name="Instagram Webhook",
            status="active",
            external_account_id="17841400000000999",
        )
        self.integration.set_credentials({"access_token": "encrypted-token"})
        self.integration.save()

    @staticmethod
    def payload(account_id="17841400000000999"):
        return {
            "object": "instagram",
            "entry": [
                {
                    "id": account_id,
                    "time": 1_724_000_000,
                    "messaging": [
                        {
                            "sender": {"id": "987654321"},
                            "recipient": {"id": account_id},
                            "timestamp": 1_724_000_000_123,
                            "message": {
                                "mid": "ig-message-1",
                                "text": "Hello from Instagram",
                            },
                        }
                    ],
                }
            ],
        }

    @staticmethod
    def signed_body(payload, secret="instagram-app-secret"):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = "sha256=" + hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        return body, signature

    def test_global_webhook_challenge_uses_server_verify_token(self):
        accepted = self.client.get(
            "/api/webhooks/instagram/",
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "instagram-verify-token",
                "hub.challenge": "13579",
            },
        )
        rejected = self.client.get(
            "/api/webhooks/instagram/",
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "13579",
            },
        )

        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.content, b"13579")
        self.assertEqual(rejected.status_code, 403)

    def test_signed_webhook_routes_by_account_dedupes_and_enqueues_on_commit(self):
        body, signature = self.signed_body(self.payload())

        with (
            patch("integrations.tasks.process_instagram_event.delay") as delay,
            self.captureOnCommitCallbacks(execute=True),
        ):
            accepted = self.client.generic(
                "POST",
                "/api/webhooks/instagram/",
                body,
                content_type="application/json",
                HTTP_X_HUB_SIGNATURE_256=signature,
            )

        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data, {"accepted": 1})
        event = IntegrationEvent.objects.get()
        self.assertEqual(event.integration, self.integration)
        self.assertEqual(event.external_event_id, "ig-message-1")
        delay.assert_called_once_with(event.pk)

        with (
            patch("integrations.tasks.process_instagram_event.delay") as replay_delay,
            self.captureOnCommitCallbacks(execute=True),
        ):
            replayed = self.client.generic(
                "POST",
                "/api/webhooks/instagram/",
                body,
                content_type="application/json",
                HTTP_X_HUB_SIGNATURE_256=signature,
            )
        self.assertEqual(replayed.data, {"accepted": 0})
        replay_delay.assert_not_called()
        self.assertEqual(IntegrationEvent.objects.count(), 1)

    def test_webhook_rejects_wrong_signature_before_parsing_or_persisting(self):
        malformed_body = b"not-json"
        wrong_signature = "sha256=" + "0" * 64

        response = self.client.generic(
            "POST",
            "/api/webhooks/instagram/",
            malformed_body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=wrong_signature,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(IntegrationEvent.objects.count(), 0)


@override_settings(**INSTAGRAM_SETTINGS)
class InstagramProcessingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="instagram-task@example.com",
            username="instagram-task",
            password="StrongPass123!",
        )
        self.integration = Integration.objects.create(
            user=self.user,
            platform="instagram",
            name="Instagram Task",
            status="active",
            external_account_id="17841400000000777",
        )
        self.client.force_authenticate(self.user)

    def test_event_task_normalizes_and_persists_incoming_message(self):
        event = IntegrationEvent.objects.create(
            integration=self.integration,
            event_type="message",
            external_event_id="ig-task-message-1",
            payload={
                "messaging": {
                    "sender": {"id": "instagram-scoped-customer"},
                    "recipient": {"id": self.integration.external_account_id},
                    "timestamp": 1_724_000_000_123,
                    "message": {
                        "mid": "ig-task-message-1",
                        "text": "Task delivery",
                    },
                }
            },
        )

        with patch(
            "integrations.services.instagram_api."
            "InstagramMessagingIntegration.get_user_profile",
            return_value={"name": "Ada Customer", "username": "ada_customer"},
        ):
            result = process_instagram_event.run(event.pk)

        self.assertEqual(result, event.pk)
        event.refresh_from_db()
        self.assertEqual(event.status, "processed")
        contact = Contact.objects.get(integration=self.integration)
        self.assertEqual(contact.external_id, "instagram-scoped-customer")
        self.assertEqual(contact.name, "Ada Customer")
        self.assertEqual(contact.username, "ada_customer")
        self.assertEqual(contact.phone, "")
        message = Message.objects.get()
        self.assertEqual(message.external_message_id, "ig-task-message-1")
        self.assertEqual(message.text, "Task delivery")
        self.assertEqual(message.sender_type, "customer")
        self.assertEqual(Notification.objects.count(), 1)

    def test_event_task_does_not_reprocess_an_already_claimed_event(self):
        event = IntegrationEvent.objects.create(
            integration=self.integration,
            event_type="message",
            external_event_id="ig-task-already-processing",
            status="processing",
        )

        with patch("integrations.services.get_adapter") as get_adapter:
            result = process_instagram_event.run(event.pk)

        self.assertEqual(result, event.pk)
        get_adapter.assert_not_called()
        event.refresh_from_db()
        self.assertEqual(event.status, "processing")

    def test_retry_task_routes_instagram_explicitly(self):
        event = IntegrationEvent.objects.create(
            integration=self.integration,
            event_type="message",
            external_event_id="ig-failed-message",
            status="failed",
        )

        with (
            patch("integrations.tasks.process_instagram_event.delay") as instagram,
            patch("integrations.tasks.process_whatsapp_event.delay") as whatsapp,
            patch("integrations.tasks.process_telegram_event.delay") as telegram,
        ):
            retry_failed_event.run()

        instagram.assert_called_once_with(event.pk)
        whatsapp.assert_not_called()
        telegram.assert_not_called()

    def test_outgoing_api_delivers_through_registered_instagram_adapter(self):
        self.integration.set_credentials(
            {
                "access_token": "outgoing-instagram-token",
                "expires_at": (timezone.now() + timedelta(days=30)).isoformat(),
            }
        )
        self.integration.save(update_fields=["credentials", "updated_at"])
        contact = Contact.objects.create(
            integration=self.integration,
            external_id="instagram-scoped-recipient",
            name="Recipient",
        )
        conversation = Conversation.objects.create(
            integration=self.integration,
            contact=contact,
            external_chat_id=contact.external_id,
        )

        with patch.object(
            InstagramAPIClient,
            "send_text",
            return_value={"message_id": "instagram-outgoing-1"},
        ) as send_text:
            response = self.client.post(
                f"/api/conversations/{conversation.pk}/messages/",
                {"text": "Reply from the business"},
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        send_text.assert_called_once_with(
            account_id=self.integration.external_account_id,
            recipient_id="instagram-scoped-recipient",
            text="Reply from the business",
            access_token="outgoing-instagram-token",
        )
        message = Message.objects.get(external_message_id="instagram-outgoing-1")
        self.assertEqual(message.sender_type, "business")
        self.assertEqual(message.text, "Reply from the business")

    def test_only_one_active_integration_can_own_instagram_account(self):
        other = User.objects.create_user(
            email="other-instagram@example.com",
            username="other-instagram",
            password="StrongPass123!",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Integration.objects.create(
                    user=other,
                    platform="instagram",
                    name="Duplicate active",
                    status="active",
                    external_account_id=self.integration.external_account_id,
                )

        duplicate_inactive = Integration.objects.create(
            user=other,
            platform="instagram",
            name="Disconnected copy",
            status="inactive",
            external_account_id=self.integration.external_account_id,
        )
        self.assertIsNotNone(duplicate_inactive.pk)


@override_settings(**INSTAGRAM_SETTINGS)
class InstagramAPIClientSecurityTests(SimpleTestCase):
    def test_profile_requests_put_access_token_in_authorization_header(self):
        client = InstagramAPIClient()

        with patch.object(client, "_request", return_value={}) as request:
            client.get_own_profile("secret-token")
            client.get_user_profile(
                instagram_scoped_id="123456",
                access_token="secret-token",
            )

        for call in request.call_args_list:
            self.assertNotIn("secret-token", call.args[0])
            self.assertNotIn("access_token=", call.args[0])
            self.assertEqual(call.kwargs["access_token"], "secret-token")

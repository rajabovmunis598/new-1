from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from contacts.models import Contact
from conversations.models import Conversation
from integrations.models import Integration
from messages.models import Message
from orders.models import Order
from users.models import User


class OpenAPIDocumentationTests(SimpleTestCase):
    def test_schema_is_public_valid_json_and_declares_jwt(self):
        response = self.client.get(
            reverse("schema"),
            HTTP_ACCEPT="application/json",
            HTTP_AUTHORIZATION="Bearer deliberately-invalid-token",
        )

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertEqual(schema["openapi"], "3.0.3")
        self.assertEqual(schema["info"]["title"], "Munis Business Hub API")
        self.assertIn("/api/auth/login/", schema["paths"])
        self.assertIn(
            "/api/integrations/telegram/connect/start/",
            schema["paths"],
        )
        self.assertIn(
            "/api/integrations/instagram/connect/start/",
            schema["paths"],
        )
        self.assertIn("/api/webhooks/instagram/", schema["paths"])
        self.assertIn("/api/search/", schema["paths"])
        self.assertEqual(
            schema["paths"]["/api/webhooks/instagram/"]["post"]["security"],
            [{}],
        )
        self.assertEqual(
            schema["components"]["securitySchemes"]["jwtAuth"],
            {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
        )
        self.assertNotIn("/api/schema/", schema["paths"])

    def test_sensitive_integration_inputs_are_write_only(self):
        response = self.client.get(reverse("schema"), HTTP_ACCEPT="application/json")
        schema = response.json()

        telegram = schema["components"]["schemas"]["TelegramStart"]
        whatsapp = schema["components"]["schemas"]["WhatsAppConnect"]
        self.assertTrue(telegram["properties"]["api_id"]["writeOnly"])
        self.assertTrue(telegram["properties"]["api_hash"]["writeOnly"])
        self.assertTrue(whatsapp["properties"]["access_token"]["writeOnly"])
        self.assertTrue(whatsapp["properties"]["app_secret"]["writeOnly"])

    def test_swagger_and_redoc_resolve_the_named_schema(self):
        swagger = self.client.get(reverse("swagger-ui"))
        redoc = self.client.get(reverse("redoc"))

        self.assertEqual(swagger.status_code, 200)
        self.assertContains(swagger, reverse("schema"))
        self.assertContains(swagger, "swagger-ui")
        self.assertEqual(redoc.status_code, 200)
        self.assertContains(redoc, reverse("schema"))
        self.assertContains(redoc, "redoc")


class DashboardStatisticsTests(APITestCase):
    def test_instagram_messages_have_their_own_count(self):
        user = User.objects.create_user(
            email="dashboard@example.com",
            username="dashboard",
            password="StrongPass123!",
        )
        integration = Integration.objects.create(
            user=user,
            platform="instagram",
            name="Instagram",
            status="active",
            external_account_id="17841400000000000",
        )
        contact = Contact.objects.create(
            integration=integration,
            external_id="123456789",
            username="customer",
        )
        conversation = Conversation.objects.create(
            integration=integration,
            contact=contact,
            external_chat_id=contact.external_id,
        )
        Message.objects.create(
            conversation=conversation,
            external_message_id="instagram-message-1",
            sender_type="customer",
            text="hello",
            external_created_at=timezone.now(),
        )
        self.client.force_authenticate(user)

        response = self.client.get("/api/dashboard/statistics/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_messages"], 1)
        self.assertEqual(response.data["instagram_messages"], 1)
        self.assertEqual(response.data["telegram_messages"], 0)
        self.assertEqual(response.data["whatsapp_messages"], 0)


class GlobalSearchTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="search-owner@example.com",
            username="search-owner",
            password="StrongPass123!",
        )
        self.integration = Integration.objects.create(
            user=self.user,
            platform="telegram",
            name="Search Telegram",
            status="active",
        )
        self.contact = Contact.objects.create(
            integration=self.integration,
            external_id="needle-contact",
            name="Needle Client",
            phone="992900001234",
        )
        self.conversation = Conversation.objects.create(
            integration=self.integration,
            contact=self.contact,
            external_chat_id="needle-chat",
            title="Needle inquiry",
        )
        Message.objects.create(
            conversation=self.conversation,
            external_message_id="needle-message",
            sender_type="customer",
            text="A needle message from the customer",
        )
        Order.objects.create(
            user=self.user,
            contact=self.contact,
            conversation=self.conversation,
            description="Needle order",
        )

        other = User.objects.create_user(
            email="search-other@example.com",
            username="search-other",
            password="StrongPass123!",
        )
        other_integration = Integration.objects.create(
            user=other,
            platform="telegram",
            name="Other Telegram",
            status="active",
        )
        Contact.objects.create(
            integration=other_integration,
            external_id="other-needle-contact",
            name="Needle Intruder",
        )
        self.client.force_authenticate(self.user)

    def test_search_returns_multiple_owner_scoped_result_types(self):
        response = self.client.get("/api/search/?q=needle")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["query"], "needle")
        self.assertEqual(
            {item["type"] for item in response.data["results"]},
            {"contact", "conversation", "order", "message"},
        )
        serialized = str(response.data["results"])
        self.assertIn("Needle Client", serialized)
        self.assertNotIn("Needle Intruder", serialized)
        self.assertIn(
            f"/messages?conversation={self.conversation.pk}",
            {item["url"] for item in response.data["results"]},
        )

    def test_blank_search_is_fast_and_empty(self):
        response = self.client.get("/api/search/?q=%20%20")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"query": "", "results": []})

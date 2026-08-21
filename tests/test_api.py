import hashlib
import hmac
import json
from django.test import override_settings
from rest_framework.test import APITestCase
from contacts.models import Contact
from conversations.models import Conversation
from integrations.models import Integration
from integrations.processing import persist_incoming

class APITests(APITestCase):
    def register(self, email="a@example.com", username="alice"):
        return self.client.post("/api/auth/register/", {"email":email, "username":username, "password":"StrongPass123!"}, format="json")
    def test_auth_and_owner_isolation(self):
        first=self.register(); self.assertEqual(first.status_code, 201)
        token=first.data["tokens"]["access"]; self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        own=Integration.objects.create(user_id=first.data["id"], platform="telegram", name="own")
        second=self.register("b@example.com", "bob"); Integration.objects.create(user_id=second.data["id"], platform="telegram", name="other")
        response=self.client.get("/api/integrations/"); self.assertEqual(response.data["count"], 1); self.assertEqual(response.data["results"][0]["id"], own.id)
    def test_encryption_and_duplicate_message(self):
        response=self.register(); user_id=response.data["id"]
        integration=Integration(user_id=user_id, platform="whatsapp", name="wa"); integration.set_credentials({"access_token":"secret"}); integration.set_session("session-secret"); integration.save()
        self.assertNotIn("secret", str(integration.credentials)); self.assertNotIn("session-secret", integration.session_data)
        data={"id":"msg-1", "from":"992001112233", "text":"hello", "type":"text"}
        one, created1=persist_incoming(integration, data); two, created2=persist_incoming(integration, data)
        self.assertTrue(created1); self.assertFalse(created2); self.assertEqual(one.id, two.id)
    def test_dashboard(self):
        response=self.register(); self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['tokens']['access']}")
        integration=Integration.objects.create(user_id=response.data["id"], platform="telegram", name="tg")
        persist_incoming(integration, {"id":"1", "chat_id":"9", "text":"hi"})
        data=self.client.get("/api/dashboard/statistics/").data
        self.assertEqual(data["total_messages"], 1); self.assertEqual(data["unread_messages"], 1)

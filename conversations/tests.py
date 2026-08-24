from asgiref.sync import async_to_sync
from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contacts.models import Contact
from core.jwt_middleware import JWTAuthMiddleware
from integrations.models import Integration
from messages.models import Message
from users.models import User

from .models import Conversation, ConversationNote


class ConversationReadTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            username="owner",
            password="StrongPass123!",
        )
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        integration = Integration.objects.create(
            user=self.user,
            platform="telegram",
            name="Owner account",
        )
        contact = Contact.objects.create(
            integration=integration,
            external_id="contact-1",
        )
        self.conversation = Conversation.objects.create(
            integration=integration,
            contact=contact,
            external_chat_id="chat-1",
        )

    def create_message(self, external_id, sender_type, is_read=False):
        return Message.objects.create(
            conversation=self.conversation,
            external_message_id=external_id,
            sender_type=sender_type,
            text=external_id,
            is_read=is_read,
        )

    def test_read_marks_only_unread_customer_messages(self):
        first = self.create_message("customer-unread-1", "customer")
        second = self.create_message("customer-unread-2", "customer")
        already_read = self.create_message("customer-read", "customer", is_read=True)
        business = self.create_message("business-unread", "business")

        response = self.client.post(
            f"/api/conversations/{self.conversation.pk}/read/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"updated": 2, "unread_count": 0})
        first.refresh_from_db()
        second.refresh_from_db()
        already_read.refresh_from_db()
        business.refresh_from_db()
        self.assertTrue(first.is_read)
        self.assertTrue(second.is_read)
        self.assertTrue(already_read.is_read)
        self.assertFalse(business.is_read)

    def test_read_cannot_update_another_users_conversation(self):
        customer_message = self.create_message("customer-unread", "customer")
        other = User.objects.create_user(
            email="other@example.com",
            username="other",
            password="StrongPass123!",
        )
        other_token = RefreshToken.for_user(other).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_token}")

        response = self.client.post(
            f"/api/conversations/{self.conversation.pk}/read/"
        )

        self.assertEqual(response.status_code, 404)
        customer_message.refresh_from_db()
        self.assertFalse(customer_message.is_read)

    def test_search_matches_contact_details(self):
        self.conversation.contact.name = "Somon Store"
        self.conversation.contact.phone = "+992900001122"
        self.conversation.contact.save(update_fields=["name", "phone"])

        by_name = self.client.get("/api/conversations/?search=Somon")
        by_phone = self.client.get("/api/conversations/?search=001122")

        self.assertEqual(by_name.status_code, 200)
        self.assertEqual(by_name.data["count"], 1)
        self.assertEqual(by_phone.data["count"], 1)


class ConversationProductivityAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="productivity-owner@example.com",
            username="productivity-owner",
            password="StrongPass123!",
        )
        self.other = User.objects.create_user(
            email="productivity-other@example.com",
            username="productivity-other",
            password="StrongPass123!",
        )
        self.conversation = self.create_conversation(
            self.user,
            "owner-chat-1",
        )
        self.other_conversation = self.create_conversation(
            self.other,
            "other-chat-1",
        )
        self.authenticate(self.user)

    def authenticate(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    @staticmethod
    def create_conversation(user, external_id):
        integration = Integration.objects.create(
            user=user,
            platform="telegram",
            name=f"{user.username} account",
        )
        contact = Contact.objects.create(
            integration=integration,
            external_id=f"contact-{external_id}",
        )
        return Conversation.objects.create(
            integration=integration,
            contact=contact,
            external_chat_id=external_id,
            title=external_id,
        )

    def test_defaults_and_priority_patch_are_serialized_and_owner_isolated(self):
        detail = self.client.get(
            f"/api/conversations/{self.conversation.pk}/"
        )
        patched = self.client.patch(
            f"/api/conversations/{self.conversation.pk}/",
            {"priority": "urgent"},
            format="json",
        )
        invalid = self.client.patch(
            f"/api/conversations/{self.conversation.pk}/",
            {"priority": "critical"},
            format="json",
        )

        self.assertEqual(detail.status_code, 200)
        self.assertFalse(detail.data["is_pinned"])
        self.assertEqual(detail.data["priority"], "normal")
        self.assertIsNone(detail.data["snoozed_until"])
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.data["priority"], "urgent")
        self.assertEqual(invalid.status_code, 400)

        hidden = self.client.patch(
            f"/api/conversations/{self.other_conversation.pk}/",
            {"priority": "high"},
            format="json",
        )
        self.assertEqual(hidden.status_code, 404)
        self.other_conversation.refresh_from_db()
        self.assertEqual(self.other_conversation.priority, "normal")

    def test_pin_unpin_actions_are_idempotent_and_pinned_rows_sort_first(self):
        newer = self.create_conversation(self.user, "owner-chat-2")

        pinned = self.client.post(
            f"/api/conversations/{self.conversation.pk}/pin/"
        )
        pinned_again = self.client.post(
            f"/api/conversations/{self.conversation.pk}/pin/"
        )
        listed = self.client.get("/api/conversations/")

        self.assertEqual(pinned.status_code, 200)
        self.assertTrue(pinned.data["is_pinned"])
        self.assertTrue(pinned_again.data["is_pinned"])
        self.assertEqual(listed.data["results"][0]["id"], self.conversation.pk)
        self.assertNotEqual(newer.pk, self.conversation.pk)

        unpinned = self.client.post(
            f"/api/conversations/{self.conversation.pk}/unpin/"
        )
        self.assertEqual(unpinned.status_code, 200)
        self.assertFalse(unpinned.data["is_pinned"])

        hidden = self.client.post(
            f"/api/conversations/{self.other_conversation.pk}/pin/"
        )
        self.assertEqual(hidden.status_code, 404)

    def test_snooze_validates_future_time_and_unsnooze_clears_it(self):
        future = timezone.now() + timedelta(hours=3)
        snoozed = self.client.post(
            f"/api/conversations/{self.conversation.pk}/snooze/",
            {"snoozed_until": future.isoformat()},
            format="json",
        )
        past = self.client.post(
            f"/api/conversations/{self.conversation.pk}/snooze/",
            {"snoozed_until": (timezone.now() - timedelta(minutes=1)).isoformat()},
            format="json",
        )

        self.assertEqual(snoozed.status_code, 200)
        self.assertIsNotNone(snoozed.data["snoozed_until"])
        self.assertEqual(past.status_code, 400)
        self.conversation.refresh_from_db()
        self.assertAlmostEqual(
            self.conversation.snoozed_until,
            future,
            delta=timedelta(seconds=1),
        )

        unsnoozed = self.client.post(
            f"/api/conversations/{self.conversation.pk}/unsnooze/"
        )
        self.assertEqual(unsnoozed.status_code, 200)
        self.assertIsNone(unsnoozed.data["snoozed_until"])

        hidden = self.client.post(
            f"/api/conversations/{self.other_conversation.pk}/snooze/",
            {"snoozed_until": future.isoformat()},
            format="json",
        )
        self.assertEqual(hidden.status_code, 404)

    def test_productivity_filters_and_ordering_stay_inside_owner(self):
        future = timezone.now() + timedelta(days=1)
        featured = self.create_conversation(self.user, "featured-chat")
        featured.is_pinned = True
        featured.priority = "urgent"
        featured.snoozed_until = future
        featured.save(
            update_fields=[
                "is_pinned",
                "priority",
                "snoozed_until",
                "updated_at",
            ]
        )
        self.other_conversation.is_pinned = True
        self.other_conversation.priority = "urgent"
        self.other_conversation.snoozed_until = future
        self.other_conversation.save(
            update_fields=[
                "is_pinned",
                "priority",
                "snoozed_until",
                "updated_at",
            ]
        )

        pinned = self.client.get("/api/conversations/?is_pinned=true")
        urgent = self.client.get("/api/conversations/?priority=urgent")
        snoozed = self.client.get("/api/conversations/?snoozed=true")
        available = self.client.get("/api/conversations/?snoozed=false")
        ordered = self.client.get("/api/conversations/?ordering=-is_pinned")
        invalid = self.client.get("/api/conversations/?snoozed=maybe")

        for response in (pinned, urgent, snoozed):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], 1)
            self.assertEqual(response.data["results"][0]["id"], featured.pk)
        self.assertEqual(available.data["count"], 1)
        self.assertEqual(
            available.data["results"][0]["id"],
            self.conversation.pk,
        )
        self.assertEqual(ordered.data["results"][0]["id"], featured.pk)
        self.assertEqual(invalid.status_code, 400)

    def test_priority_ordering_uses_declared_enum_order(self):
        low = self.create_conversation(self.user, "priority-low")
        low.priority = "low"
        low.save(update_fields=["priority", "updated_at"])
        high = self.create_conversation(self.user, "priority-high")
        high.priority = "high"
        high.save(update_fields=["priority", "updated_at"])
        urgent = self.create_conversation(self.user, "priority-urgent")
        urgent.priority = "urgent"
        urgent.save(update_fields=["priority", "updated_at"])

        ascending = self.client.get("/api/conversations/?ordering=priority")
        descending = self.client.get("/api/conversations/?ordering=-priority")

        self.assertEqual(
            [item["priority"] for item in ascending.data["results"]],
            ["low", "normal", "high", "urgent"],
        )
        self.assertEqual(
            [item["priority"] for item in descending.data["results"]],
            ["urgent", "high", "normal", "low"],
        )

    def test_notes_create_and_list_are_owner_isolated(self):
        created = self.client.post(
            f"/api/conversations/{self.conversation.pk}/notes/",
            {"text": "  Call this customer tomorrow.  ", "author": self.other.pk},
            format="json",
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["conversation"], self.conversation.pk)
        self.assertEqual(created.data["author"], self.user.pk)
        self.assertEqual(created.data["author_username"], self.user.username)
        self.assertEqual(created.data["text"], "Call this customer tomorrow.")
        note = ConversationNote.objects.get()
        self.assertEqual(note.author, self.user)

        listed = self.client.get(
            f"/api/conversations/{self.conversation.pk}/notes/"
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(listed.data["results"][0]["id"], note.pk)

        blank = self.client.post(
            f"/api/conversations/{self.conversation.pk}/notes/",
            {"text": "   "},
            format="json",
        )
        self.assertEqual(blank.status_code, 400)

        self.authenticate(self.other)
        hidden_list = self.client.get(
            f"/api/conversations/{self.conversation.pk}/notes/"
        )
        hidden_create = self.client.post(
            f"/api/conversations/{self.conversation.pk}/notes/",
            {"text": "Not allowed"},
            format="json",
        )
        self.assertEqual(hidden_list.status_code, 404)
        self.assertEqual(hidden_create.status_code, 404)
        self.assertEqual(ConversationNote.objects.count(), 1)

    def test_note_delete_requires_owned_conversation_and_own_author(self):
        own_note = ConversationNote.objects.create(
            conversation=self.conversation,
            author=self.user,
            text="Owner note",
        )
        another_authors_note = ConversationNote.objects.create(
            conversation=self.conversation,
            author=self.other,
            text="Another author's note",
        )

        cannot_delete_other_author = self.client.delete(
            f"/api/conversations/{self.conversation.pk}/notes/"
            f"{another_authors_note.pk}/"
        )
        wrong_parent = self.client.delete(
            f"/api/conversations/{self.other_conversation.pk}/notes/{own_note.pk}/"
        )
        deleted = self.client.delete(
            f"/api/conversations/{self.conversation.pk}/notes/{own_note.pk}/"
        )

        self.assertEqual(cannot_delete_other_author.status_code, 404)
        self.assertEqual(wrong_parent.status_code, 404)
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(ConversationNote.objects.filter(pk=own_note.pk).exists())
        self.assertTrue(
            ConversationNote.objects.filter(pk=another_authors_note.pk).exists()
        )


class ConversationProductivityOpenAPITests(SimpleTestCase):
    def test_schema_exposes_productivity_fields_actions_and_notes(self):
        schema = self.client.get(
            "/api/schema/",
            HTTP_ACCEPT="application/json",
        ).json()

        conversation = schema["components"]["schemas"]["Conversation"]
        for field in ("is_pinned", "priority", "snoozed_until"):
            self.assertIn(field, conversation["properties"])
        self.assertIn("/api/conversations/{id}/pin/", schema["paths"])
        self.assertIn("/api/conversations/{id}/unpin/", schema["paths"])
        self.assertIn("/api/conversations/{id}/snooze/", schema["paths"])
        self.assertIn("/api/conversations/{id}/unsnooze/", schema["paths"])
        self.assertIn("/api/conversations/{conversation_pk}/notes/", schema["paths"])
        self.assertIn(
            "/api/conversations/{conversation_pk}/notes/{note_id}/",
            schema["paths"],
        )
        self.assertIn("ConversationNote", schema["components"]["schemas"])
        parameters = schema["paths"]["/api/conversations/"]["get"]["parameters"]
        self.assertIn("snoozed", {parameter["name"] for parameter in parameters})


class JWTAuthMiddlewareTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="socket@example.com",
            username="socket-user",
            password="StrongPass123!",
        )

    def middleware_user(self, query_string, fallback_user=None):
        captured = {}

        async def inner(scope, receive, send):
            captured["user"] = scope.get("user")

        scope = {"type": "websocket", "query_string": query_string}
        if fallback_user is not None:
            scope["user"] = fallback_user
        async_to_sync(JWTAuthMiddleware(inner))(scope, None, None)
        return captured["user"]

    def test_valid_access_token_authenticates_user(self):
        token = str(RefreshToken.for_user(self.user).access_token)

        user = self.middleware_user(f"token={token}".encode())

        self.assertEqual(user.pk, self.user.pk)
        self.assertTrue(user.is_authenticated)

    def test_invalid_or_refresh_token_is_anonymous(self):
        invalid_user = self.middleware_user(
            b"token=not-a-jwt",
            fallback_user=self.user,
        )
        refresh_user = self.middleware_user(
            f"token={RefreshToken.for_user(self.user)}".encode(),
            fallback_user=self.user,
        )

        self.assertIsInstance(invalid_user, AnonymousUser)
        self.assertIsInstance(refresh_user, AnonymousUser)

    def test_missing_token_preserves_session_user(self):
        user = self.middleware_user(b"", fallback_user=self.user)

        self.assertIs(user, self.user)

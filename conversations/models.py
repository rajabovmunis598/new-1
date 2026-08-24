from django.conf import settings
from django.db import models

from integrations.security import decrypt_json, encrypt_json


class Conversation(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("closed", "Closed"),
        ("archived", "Archived"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    integration = models.ForeignKey(
        "integrations.Integration",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    external_chat_id = models.CharField(max_length=255)
    external_peer_data = models.TextField(blank=True)
    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    is_pinned = models.BooleanField(default=False, db_index=True)
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="normal",
        db_index=True,
    )
    snoozed_until = models.DateTimeField(null=True, blank=True, db_index=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversations"
        ordering = ["-last_message_at"]
        unique_together = ["integration", "external_chat_id"]
        indexes = [
            models.Index(fields=["integration", "external_chat_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-last_message_at"]),
        ]

    def __str__(self):
        return self.title or f"Conversation {self.external_chat_id}"

    def set_external_peer(self, value):
        self.external_peer_data = encrypt_json(value) if value else ""

    def get_external_peer(self):
        return decrypt_json(self.external_peer_data) if self.external_peer_data else {}


class ConversationNote(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_notes",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversation_notes"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["conversation", "-created_at"]),
            models.Index(fields=["author"]),
        ]

    def __str__(self):
        return f"Note {self.pk} on conversation {self.conversation_id}"

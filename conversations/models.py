from django.db import models


class Conversation(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("closed", "Closed"),
        ("archived", "Archived"),
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
    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
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

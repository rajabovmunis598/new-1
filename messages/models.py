from django.db import models


class Message(models.Model):
    SENDER_TYPE_CHOICES = [
        ("customer", "Customer"),
        ("business", "Business"),
        ("system", "System"),
    ]
    MESSAGE_TYPE_CHOICES = [
        ("text", "Text"),
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("document", "Document"),
        ("location", "Location"),
        ("sticker", "Sticker"),
        ("other", "Other"),
    ]

    conversation = models.ForeignKey(
        "conversations.Conversation",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    external_message_id = models.CharField(max_length=255)
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPE_CHOICES)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default="text")
    text = models.TextField(blank=True)
    media_url = models.URLField(blank=True)
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    external_created_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "messages"
        ordering = ["-created_at"]
        unique_together = ["conversation", "external_message_id"]
        indexes = [
            models.Index(fields=["conversation", "external_message_id"]),
            models.Index(fields=["sender_type"]),
            models.Index(fields=["message_type"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.sender_type}: {self.text[:50]}"

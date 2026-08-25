from django.conf import settings
from django.db import models
from .security import decrypt_json, encrypt_json


class Integration(models.Model):
    PLATFORM_CHOICES = [
        ("telegram", "Telegram"),
        ("whatsapp", "WhatsApp"),
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("viber", "Viber"),
        ("vk", "VK"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("error", "Error"),
        ("pending", "Pending"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="integrations",
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    external_account_id = models.CharField(max_length=255, blank=True)
    credentials = models.JSONField(default=dict, blank=True)
    session_data = models.TextField(blank=True)
    webhook_url = models.URLField(blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integrations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "platform"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["external_account_id"],
                condition=(
                    models.Q(platform="instagram", status="active")
                    & ~models.Q(external_account_id="")
                ),
                name="uniq_active_instagram_account",
            ),
            models.UniqueConstraint(
                fields=["external_account_id"],
                condition=(
                    models.Q(platform="facebook", status="active")
                    & ~models.Q(external_account_id="")
                ),
                name="uniq_active_facebook_account",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.platform})"

    def set_credentials(self, value):
        self.credentials = {"encrypted": encrypt_json(value)}

    def get_credentials(self):
        token = self.credentials.get("encrypted") if isinstance(self.credentials, dict) else None
        return decrypt_json(token) if token else {}

    def set_session(self, value):
        self.session_data = encrypt_json({"session": value})

    def get_session(self):
        return decrypt_json(self.session_data).get("session", "") if self.session_data else ""

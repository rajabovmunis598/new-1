from django.db import models


class Contact(models.Model):
    integration = models.ForeignKey(
        "integrations.Integration",
        on_delete=models.CASCADE,
        related_name="contacts",
    )
    external_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255, blank=True)
    username = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    avatar_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contacts"
        ordering = ["-created_at"]
        unique_together = ["integration", "external_id"]
        indexes = [
            models.Index(fields=["integration", "external_id"]),
            models.Index(fields=["name"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self):
        return self.name or self.username or self.external_id

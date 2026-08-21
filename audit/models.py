from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "entity_type"]),
            models.Index(fields=["-created_at"]),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.entity_type}"


class IntegrationEvent(models.Model):
    STATUS_CHOICES = [
        ("received", "Received"),
        ("processing", "Processing"),
        ("processed", "Processed"),
        ("failed", "Failed"),
    ]

    integration = models.ForeignKey(
        "integrations.Integration",
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=100)
    external_event_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="received")
    error_message = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "integration_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["integration", "status"]),
            models.Index(fields=["-created_at"]),
        ]
        constraints = [models.UniqueConstraint(fields=["integration", "external_event_id"], condition=~models.Q(external_event_id=""), name="unique_integration_external_event")]

    def __str__(self):
        return f"{self.event_type} - {self.status}"

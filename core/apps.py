from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Register schema-only extensions without changing application APIs.
        from . import openapi  # noqa: F401

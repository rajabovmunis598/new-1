from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.csv_exports import csv_export_response

from .models import Contact
from .serializers import ContactSerializer


class ContactViewSet(ReadOnlyModelViewSet):
    queryset = Contact.objects.none()
    serializer_class = ContactSerializer
    filterset_fields = ("integration",)
    search_fields = ("name", "username", "phone")
    ordering_fields = ("name", "created_at")

    def get_queryset(self):
        return Contact.objects.filter(
            integration__user=self.request.user
        ).select_related("integration")

    @extend_schema(
        operation_id="contacts_export_csv",
        summary="Export the authenticated user's filtered contacts as CSV",
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
        tags=["contacts"],
    )
    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        contacts = self.filter_queryset(self.get_queryset())
        headers = (
            "id",
            "platform",
            "integration_id",
            "integration_name",
            "external_id",
            "name",
            "username",
            "phone",
            "avatar_url",
            "created_at",
            "updated_at",
        )
        rows = (
            (
                contact.pk,
                contact.integration.platform,
                contact.integration_id,
                contact.integration.name,
                contact.external_id,
                contact.name,
                contact.username,
                contact.phone,
                contact.avatar_url,
                contact.created_at,
                contact.updated_at,
            )
            for contact in contacts
        )
        return csv_export_response("contacts", headers, rows)

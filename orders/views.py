from decimal import Decimal

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from core.csv_exports import csv_export_response

from .models import Order
from .serializers import OrderSerializer


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.none()
    serializer_class = OrderSerializer
    filterset_fields = ("status", "contact", "conversation", "currency")
    search_fields = ("external_id", "description", "contact__name", "contact__phone")
    ordering_fields = ("created_at", "amount", "status")

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("contact__integration", "conversation")
            .prefetch_related("items")
        )

    @extend_schema(
        operation_id="orders_export_csv",
        summary="Export the authenticated user's filtered orders as CSV",
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
        tags=["orders"],
    )
    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        orders = self.filter_queryset(self.get_queryset())
        headers = (
            "id",
            "external_id",
            "status",
            "description",
            "amount",
            "currency",
            "platform",
            "contact_id",
            "contact_name",
            "contact_phone",
            "conversation_id",
            "item_count",
            "items_total",
            "completed_at",
            "created_at",
            "updated_at",
        )

        def rows():
            for order in orders:
                items = list(order.items.all())
                yield (
                    order.pk,
                    order.external_id,
                    order.status,
                    order.description,
                    order.amount,
                    order.currency,
                    order.contact.integration.platform,
                    order.contact_id,
                    order.contact.name,
                    order.contact.phone,
                    order.conversation_id,
                    len(items),
                    sum((item.total for item in items), Decimal("0.00")),
                    order.completed_at,
                    order.created_at,
                    order.updated_at,
                )

        return csv_export_response("orders", headers, rows())

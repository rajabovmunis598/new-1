import csv
import io
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from contacts.models import Contact
from integrations.models import Integration
from users.models import User

from .models import Order, OrderItem


def csv_rows(response):
    content = response.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    return reader.fieldnames, list(reader)


class OrderCSVExportTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="orders-export@example.com",
            username="orders-export",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            email="orders-foreign@example.com",
            username="orders-foreign",
            password="StrongPass123!",
        )
        self.integration = Integration.objects.create(
            user=self.user,
            platform="whatsapp",
            name="Owner WhatsApp",
            status="active",
        )
        self.other_integration = Integration.objects.create(
            user=self.other_user,
            platform="telegram",
            name="Foreign Telegram",
            status="active",
        )
        self.contact = Contact.objects.create(
            integration=self.integration,
            external_id="orders-contact-1",
            name="@Owner Customer",
            phone="+992900000002",
        )
        self.other_contact = Contact.objects.create(
            integration=self.other_integration,
            external_id="orders-contact-foreign",
            name="Foreign Customer",
        )
        self.matching_order = Order.objects.create(
            user=self.user,
            contact=self.contact,
            external_id="order-export-1",
            description='=HYPERLINK("https://example.test","needle order")',
            amount=Decimal("12.50"),
            currency="TJS",
            status="completed",
            completed_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=self.matching_order,
            name="First item",
            quantity=2,
            price=Decimal("3.00"),
        )
        OrderItem.objects.create(
            order=self.matching_order,
            name="Second item",
            quantity=1,
            price=Decimal("4.00"),
        )
        Order.objects.create(
            user=self.user,
            contact=self.contact,
            external_id="order-export-2",
            description="Different order",
            amount=Decimal("20.00"),
            currency="USD",
            status="new",
        )
        Order.objects.create(
            user=self.other_user,
            contact=self.other_contact,
            external_id="order-foreign",
            description="needle order owned by somebody else",
            amount=Decimal("1.00"),
            currency="TJS",
            status="completed",
        )
        self.client.force_authenticate(self.user)

    def test_export_matches_list_filters_and_flattens_order_summary(self):
        query = "?status=completed&currency=TJS&search=needle&ordering=amount"
        listed = self.client.get(f"/api/orders/{query}")
        exported = self.client.get(f"/api/orders/export/{query}")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(exported["Cache-Control"], "no-store")
        self.assertEqual(
            exported["Content-Disposition"],
            f'attachment; filename="orders-{timezone.localdate().isoformat()}.csv"',
        )

        fieldnames, rows = csv_rows(exported)
        self.assertEqual(
            fieldnames,
            [
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
            ],
        )
        listed_ids = [str(item["id"]) for item in listed.data["results"]]
        self.assertEqual([row["id"] for row in rows], listed_ids)
        self.assertEqual(rows[0]["id"], str(self.matching_order.pk))
        self.assertTrue(rows[0]["description"].startswith("'="))
        self.assertEqual(rows[0]["contact_name"], "'@Owner Customer")
        self.assertEqual(rows[0]["contact_phone"], "'+992900000002")
        self.assertEqual(rows[0]["item_count"], "2")
        self.assertEqual(rows[0]["items_total"], "10.00")

    def test_foreign_contact_filter_cannot_export_foreign_orders(self):
        response = self.client.get(
            f"/api/orders/export/?contact={self.other_contact.pk}"
        )

        self.assertEqual(response.status_code, 200)
        _, rows = csv_rows(response)
        self.assertEqual(rows, [])

    def test_export_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/orders/export/")

        self.assertEqual(response.status_code, 401)

import csv
import io

from django.test import SimpleTestCase
from django.utils import timezone
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APITestCase

from integrations.models import Integration
from users.models import User

from .models import Contact


def csv_rows(response):
    content = response.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    return reader.fieldnames, list(reader)


class ContactCSVExportTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="contacts-export@example.com",
            username="contacts-export",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            email="contacts-foreign@example.com",
            username="contacts-foreign",
            password="StrongPass123!",
        )
        self.integration = Integration.objects.create(
            user=self.user,
            platform="telegram",
            name="Owner Telegram",
            status="active",
        )
        self.other_integration = Integration.objects.create(
            user=self.other_user,
            platform="whatsapp",
            name="Foreign WhatsApp",
            status="active",
        )
        self.matching_contact = Contact.objects.create(
            integration=self.integration,
            external_id="contact-export-1",
            name='=HYPERLINK("https://example.test","Customer")',
            username="needle_customer",
            phone="+992900000001",
        )
        Contact.objects.create(
            integration=self.integration,
            external_id="contact-export-2",
            name="Not included",
            username="different",
        )
        Contact.objects.create(
            integration=self.other_integration,
            external_id="contact-foreign",
            name="Foreign matching contact",
            username="needle_customer",
        )
        self.client.force_authenticate(self.user)

    def test_export_matches_list_filters_and_has_safe_download_headers(self):
        query = (
            f"?integration={self.integration.pk}"
            "&search=needle&ordering=name"
        )
        listed = self.client.get(f"/api/contacts/{query}")
        exported = self.client.get(f"/api/contacts/export/{query}")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(exported["Cache-Control"], "no-store")
        self.assertEqual(exported["X-Content-Type-Options"], "nosniff")
        self.assertEqual(
            exported["Content-Disposition"],
            f'attachment; filename="contacts-{timezone.localdate().isoformat()}.csv"',
        )

        fieldnames, rows = csv_rows(exported)
        self.assertEqual(
            fieldnames,
            [
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
            ],
        )
        listed_ids = [str(item["id"]) for item in listed.data["results"]]
        self.assertEqual([row["id"] for row in rows], listed_ids)
        self.assertEqual(rows[0]["id"], str(self.matching_contact.pk))
        self.assertEqual(rows[0]["platform"], "telegram")
        self.assertTrue(rows[0]["name"].startswith("'="))
        self.assertEqual(rows[0]["phone"], "'+992900000001")

    def test_foreign_integration_filter_cannot_export_foreign_contacts(self):
        response = self.client.get(
            f"/api/contacts/export/?integration={self.other_integration.pk}"
        )

        self.assertEqual(response.status_code, 200)
        _, rows = csv_rows(response)
        self.assertEqual(rows, [])

    def test_export_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/contacts/export/")

        self.assertEqual(response.status_code, 401)


class CSVExportOpenAPITests(SimpleTestCase):
    def test_exports_are_documented_as_csv_downloads(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)

        for path in ("/api/contacts/export/", "/api/orders/export/"):
            operation = schema["paths"][path]["get"]
            self.assertIn("text/csv", operation["responses"]["200"]["content"])
            self.assertTrue(operation["security"])

from django.test import SimpleTestCase
from django.contrib.staticfiles import finders
from django.urls import reverse


class FrontendViewTests(SimpleTestCase):
    def test_root_renders_application_shell(self):
        response = self.client.get(reverse("frontend"))
        self.assertContains(response, "Munis Business Hub")
        self.assertContains(response, 'id="app"')

    def test_client_side_route_renders_application_shell(self):
        for route in ("/login", "/register", "/dashboard", "/messages", "/contacts", "/orders", "/integrations", "/settings"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertContains(response, "Munis Business Hub")

    def test_frontend_static_assets_are_discoverable(self):
        for asset in (
            "frontend/css/app.css",
            "frontend/css/landing.css",
            "frontend/js/app.js",
            "frontend/js/pages/landing.js",
        ):
            with self.subTest(asset=asset):
                self.assertIsNotNone(finders.find(asset))

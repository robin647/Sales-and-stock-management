from types import SimpleNamespace

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIClient


class RootStatusTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_root_returns_public_status_json(self):
        response = self.client.get(reverse("root-status"), secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Sales and Stock Management API is running",
            },
        )

    def test_existing_api_routes_still_resolve(self):
        route_names = (
            "health",
            "token_obtain_pair",
            "showroom_login",
            "token_refresh",
            "me",
            "showroom-list",
            "product-list",
            "product-category-list",
            "daily-stock-list",
            "daily-balance-list",
            "dashboard",
            "daily-statement",
            "monthly-report",
            "export-daily",
            "export-monthly",
            "admin:index",
        )

        for route_name in route_names:
            with self.subTest(route=route_name):
                self.assertTrue(reverse(route_name))

    def test_existing_health_and_protected_api_routes_still_respond(self):
        health_response = self.client.get(reverse("health"), secure=True)
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json(), {"status": "ok"})

        protected_routes = (
            "me",
            "showroom-list",
            "product-list",
            "daily-stock-list",
            "daily-balance-list",
            "dashboard",
        )
        for route_name in protected_routes:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name), secure=True)
                self.assertEqual(response.status_code, 401)

    def test_existing_authentication_and_permissions_are_unchanged(self):
        unauthenticated = self.client.get(reverse("me"), secure=True)
        self.assertEqual(unauthenticated.status_code, 401)

        showroom_user = SimpleNamespace(
            is_authenticated=True,
            role="showroom_user",
        )
        self.client.force_authenticate(user=showroom_user)

        admin_only_route = self.client.get(reverse("showroom-user-list"), secure=True)
        self.assertEqual(admin_only_route.status_code, 403)

        admin_only_write = self.client.post(
            reverse("product-list"), {}, format="json", secure=True
        )
        self.assertEqual(admin_only_write.status_code, 403)

    def test_unknown_route_returns_404(self):
        response = self.client.get("/this-route-does-not-exist/", secure=True)

        self.assertEqual(response.status_code, 404)


class CorsPreflightTests(SimpleTestCase):
    def test_login_preflight_allows_vercel_frontend(self):
        response = APIClient().options(
            reverse("token_obtain_pair"),
            secure=True,
            HTTP_ORIGIN="https://sales-and-stock-management-s7d7.vercel.app",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            "https://sales-and-stock-management-s7d7.vercel.app",
        )
        self.assertIn("POST", response["Access-Control-Allow-Methods"])

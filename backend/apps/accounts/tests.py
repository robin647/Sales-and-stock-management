from django.urls import reverse
from rest_framework.test import APIClient

from django.test import TestCase
from .models import User


class CustomerSignupTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_customer_can_sign_up_and_log_in_with_mobile_number(self):
        response = self.client.post(
            reverse("customer-signup"),
            {
                "name": "Mahir Customer",
                "email": "customer@example.com",
                "phone_number": "01700 123456",
                "password": "MahirPass#2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="01700123456")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertEqual(user.phone_number, "01700123456")
        self.assertTrue(user.check_password("MahirPass#2026"))

        login_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": "MahirPass#2026"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.data["access"].count("."), 2)

    def test_duplicate_mobile_number_cannot_register_twice(self):
        User.objects.create_user(
            username="01700123456",
            password="MahirPass#2026",
            role=User.Role.CUSTOMER,
            phone_number="01700123456",
        )
        response = self.client.post(
            reverse("customer-signup"),
            {
                "name": "Another Customer",
                "email": "another@example.com",
                "phone_number": "01700 123456",
                "password": "AnotherPass#2026",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_customer_cannot_access_staff_inventory_or_reports(self):
        customer = User.objects.create_user(
            username="01700123456",
            password="MahirPass#2026",
            role=User.Role.CUSTOMER,
            phone_number="01700123456",
        )
        self.client.force_authenticate(customer)

        for route_name in ("daily-stock-list", "dashboard"):
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 403)
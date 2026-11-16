from django.urls import reverse
from rest_framework.test import APIClient

from django.test import TestCase, override_settings
from .models import User


class CustomerSignupTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_customer_can_sign_up_only_after_email_verification(self):
        import re
        from django.core import mail
        from django.core.cache import cache
        cache.clear()
        sent = self.client.post(reverse('email-otp-request'), {'email': 'customer@example.com', 'purpose': 'signup'}, format='json')
        self.assertEqual(sent.status_code, 200, sent.data)
        code = re.search(r'\b([0-9]{6})\b', mail.outbox[-1].body).group(1)
        response = self.client.post(reverse('customer-signup'), {
            'name': 'Mahir Customer', 'email': 'customer@example.com', 'phone_number': '01700 123456',
            'password': 'MahirPass#2026', 'otp': code,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(email='customer@example.com')
        self.assertTrue(user.email_verified)
        self.assertEqual(user.phone_number, '01700123456')
        response = self.client.post(reverse('customer-login'), {'email': user.email, 'password': 'MahirPass#2026'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['access'].count('.'), 2)

    def test_existing_email_cannot_register_twice(self):
        User.objects.create_user(username='existing-phone',email='customer@example.com',role='customer')
        response = self.client.post(reverse('customer-signup'), {'name':'Another Customer','email':'customer@example.com','password':'AnotherPass#2026','otp':'123456'}, format='json')
        self.assertEqual(response.status_code,400)
        self.assertEqual(User.objects.filter(email='customer@example.com').count(),1)

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

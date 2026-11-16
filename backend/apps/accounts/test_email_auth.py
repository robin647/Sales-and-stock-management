import base64
import json
import re
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch, MagicMock
from uuid import uuid4
from django.core import mail
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.shop.models import Order
from .models import User, EmailVerification, OtpSendBudget
from .email_backend import GmailApiEmailBackend


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.email = "customer@example.com"
        self.password = "UniqueCustomerPassword#823"

    def request(self, email=None, purpose="signup"):
        return self.client.post(reverse("email-otp-request"), {"email": email or self.email, "purpose": purpose}, format="json")

    def code(self):
        return re.search(r"\b([0-9]{6})\b", mail.outbox[-1].body).group(1)

    def signup(self, code=None, **changes):
        return self.client.post(reverse("customer-signup"), {"name": "Test Customer", "email": self.email,
            "password": self.password, "otp": code if code is not None else self.code(), **changes}, format="json")

    def test_request_sends_six_digits_without_creating_user_or_exposing_code(self):
        response = self.request()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["expires_in"], 60)
        self.assertFalse(User.objects.exists())
        self.assertEqual(len(self.code()), 6)
        self.assertNotIn(self.code(), str(response.data))
        verification = EmailVerification.objects.get()
        self.assertNotEqual(verification.code_hash, self.code())
        self.assertEqual(len(verification.code_hash), 64)
        self.assertTrue(verification.ready)
        self.assertEqual(mail.outbox[-1].to, [self.email])
        self.assertLessEqual((verification.expires_at - timezone.now()).total_seconds(), 60)

    def test_signup_requires_code_and_code_can_only_be_used_once(self):
        response = self.client.post(reverse("customer-signup"), {"name": "Buyer", "email": self.email, "password": self.password}, format="json")
        self.assertEqual(response.status_code, 400)
        self.request(); code = self.code()
        response = self.signup(code)
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(email=self.email)
        self.assertTrue(user.email_verified)
        self.assertTrue(user.check_password(self.password))
        self.assertTrue(EmailVerification.objects.get().consumed)
        self.assertEqual(self.signup(code).status_code, 400)
        self.assertEqual(User.objects.count(), 1)

    def test_wrong_attempts_persist_and_lock_code_after_five_failures(self):
        self.request(); code = self.code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.assertEqual(self.signup(wrong).status_code, 400)
        self.assertEqual(EmailVerification.objects.get().attempts, 5)
        cache.clear()  # Exercise the persisted OTP lock independently of request throttling.
        self.assertEqual(self.signup(code).status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_expired_code_does_not_register(self):
        self.request()
        EmailVerification.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.signup().status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_code_is_bound_to_its_email(self):
        self.request()
        self.assertEqual(self.signup(email="different@example.com").status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_resend_wait_and_invalidation(self):
        with patch("apps.accounts.email_verification.secrets.randbelow", side_effect=[123456, 654321]):
            self.assertEqual(self.request().status_code, 200)
            EmailVerification.objects.update(sent_at=timezone.now() - timedelta(seconds=61))
            self.assertEqual(self.request().status_code, 200)
        self.assertEqual(self.signup("123456").status_code, 400)
        self.assertEqual(self.signup("654321").status_code, 201)

    def test_immediate_resend_is_throttled(self):
        self.request()
        self.assertEqual(self.request().status_code, 429)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(OTP_DAILY_EMAIL_LIMIT=1)
    def test_daily_send_budget_is_persisted(self):
        self.assertEqual(self.request().status_code, 200)
        self.assertEqual(self.request("another@example.com").status_code, 503)
        self.assertEqual(OtpSendBudget.objects.get().reserved, 1)

    def test_hourly_per_email_limit_survives_resends(self):
        self.request()
        EmailVerification.objects.update(sent_at=timezone.now() - timedelta(seconds=61), sent_count=5)
        self.assertEqual(self.request().status_code, 429)

    def test_delivery_failure_is_closed_and_does_not_leak_credentials(self):
        with patch("apps.accounts.email_verification.send_mail", side_effect=RuntimeError("secret-provider-password")):
            response = self.request()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret-provider-password", str(response.data))
        self.assertFalse(EmailVerification.objects.get().ready)
        self.assertFalse(User.objects.exists())

    def test_normalization_and_optional_contact_phone(self):
        self.assertEqual(self.request(" Customer@Example.COM ").status_code, 200)
        self.assertEqual(self.signup(email="CUSTOMER@example.com").status_code, 201)
        self.assertTrue(User.objects.filter(email=self.email, phone_number="").exists())

    def test_verified_customer_logs_in_with_email_not_phone(self):
        self.request(); self.signup(phone_number="01712345678")
        response = self.client.post(reverse("customer-login"), {"email": "CUSTOMER@example.com", "password": self.password}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        user = User.objects.get(email=self.email)
        response = self.client.post(reverse("token_obtain_pair"), {"username": user.username, "password": self.password}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_old_customer_verifies_same_account_and_keeps_orders(self):
        user = User.objects.create_user("01712345678", email=self.email, password=self.password, role="customer")
        order = Order.objects.create(customer=user, request_key=uuid4(), recipient_name="Old buyer", phone="01712345678", address="Dhaka", city="Dhaka", subtotal=1000, shipping_fee=120, total=1120)
        response = self.client.post(reverse("customer-login"), {"email": self.email, "password": self.password}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.request(purpose="verify").status_code, 200)
        response = self.client.post(reverse("email-otp-verify"), {"email": self.email, "otp": self.code()}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        user.refresh_from_db(); order.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertEqual(user.username, "01712345678")
        self.assertEqual(order.customer_id, user.pk)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.client.post(reverse("customer-login"), {"email": self.email, "password": self.password}, format="json").status_code, 200)

    def test_duplicate_legacy_emails_are_not_silently_merged(self):
        User.objects.create_user("old-one", email=self.email, role="customer")
        User.objects.create_user("old-two", email=self.email, role="customer")
        self.assertEqual(self.request(purpose="verify").status_code, 400)
        self.assertEqual(User.objects.count(), 2)

    def test_staff_and_customer_login_endpoints_are_separate(self):
        admin = User.objects.create_user("owner", email="owner@example.com", password=self.password, role="admin")
        self.assertEqual(self.client.post(reverse("customer-login"), {"email": admin.email, "password": self.password}, format="json").status_code, 401)
        self.assertEqual(self.client.post(reverse("token_obtain_pair"), {"username": admin.username, "password": self.password}, format="json").status_code, 200)

    def test_unverified_customer_cannot_refresh_old_session(self):
        user = User.objects.create_user("old-customer", email=self.email, role="customer")
        refresh = RefreshToken.for_user(user)
        self.assertEqual(self.client.post(reverse("token_refresh"), {"refresh": str(refresh)}, format="json").status_code, 401)

    def test_password_validation_does_not_consume_valid_code(self):
        self.request(); code = self.code()
        self.assertEqual(self.signup(code, password="password").status_code, 400)
        self.assertFalse(EmailVerification.objects.get().consumed)
        self.assertEqual(self.signup(code).status_code, 201)


@override_settings(GMAIL_CLIENT_ID="test-client", GMAIL_CLIENT_SECRET="test-secret", GMAIL_REFRESH_TOKEN="test-refresh", EMAIL_TIMEOUT=5)
class GmailTransportTests(SimpleTestCase):
    def test_mail_is_mime_encoded_and_sent_over_https(self):
        token = MagicMock(); token.__enter__.return_value = BytesIO(b'{"access_token":"test-access"}')
        sent = MagicMock(); sent.__enter__.return_value = BytesIO(b'{"id":"message-id"}')
        with patch("apps.accounts.email_backend.urlopen", side_effect=[token, sent]) as network:
            message = EmailMessage("Code", "Your code is 123456", "mhrobin471@gmail.com", ["customer@example.com"])
            self.assertEqual(GmailApiEmailBackend().send_messages([message]), 1)
        self.assertEqual(network.call_count, 2)
        request = network.call_args_list[1].args[0]
        self.assertTrue(request.full_url.startswith("https://gmail.googleapis.com/"))
        raw = json.loads(request.data)["raw"]
        self.assertIn("123456", base64.urlsafe_b64decode(raw).decode())

    @override_settings(GMAIL_REFRESH_TOKEN="")
    def test_missing_configuration_fails_without_network(self):
        from django.core.exceptions import ImproperlyConfigured
        with patch("apps.accounts.email_backend.urlopen") as network:
            with self.assertRaises(ImproperlyConfigured):
                GmailApiEmailBackend().send_messages([EmailMessage("Test", "Body", "sender@example.com", ["to@example.com"])])
            network.assert_not_called()

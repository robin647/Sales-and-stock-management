from io import BytesIO
from unittest.mock import patch
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import caches
from django.http import JsonResponse
from django.test import SimpleTestCase, TestCase, RequestFactory, override_settings
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.models import User
from core.excel import protect_workbook
from core.security import RequestGuardMiddleware, client_ip
from core.permissions import IsAdminOrOwnShowroom


@override_settings(REQUEST_GUARD_ENABLED=True, REQUESTS_PER_MINUTE=4, AUTH_REQUESTS_PER_MINUTE=2)
class RequestGuardTests(SimpleTestCase):
    def setUp(self):
        caches['security'].clear()
        self.factory = RequestFactory()
        self.guard = RequestGuardMiddleware(lambda request: JsonResponse({'ok': True}))

    def request(self, path='/api/products/', method='get', **extra):
        return self.guard(getattr(self.factory, method)(path, **extra))

    def test_global_limit_and_retry_header(self):
        for _ in range(4):
            self.assertEqual(self.request().status_code, 200)
        response = self.request()
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)
        self.assertEqual(self.request('/api/health/').status_code, 200)

    def test_auth_limit_covers_refresh_and_admin_login(self):
        self.assertEqual(self.request('/api/auth/refresh/', 'post').status_code, 200)
        self.assertEqual(self.request('/admin/login/', 'post').status_code, 200)
        self.assertEqual(self.request('/api/auth/customer/login/', 'post').status_code, 429)

    def test_forged_forwarded_headers_do_not_bypass_default_limit(self):
        for number in range(4):
            self.assertEqual(self.request(HTTP_X_FORWARDED_FOR=f'198.51.100.{number}').status_code, 200)
        self.assertEqual(self.request(HTTP_X_FORWARDED_FOR='203.0.113.1').status_code, 429)

    @override_settings(REST_FRAMEWORK={'NUM_PROXIES': 1})
    def test_only_trusted_proxy_position_is_used(self):
        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='attacker-string, 198.51.100.4')
        self.assertEqual(client_ip(request), '198.51.100.4')

    def test_body_and_query_limits_happen_before_view(self):
        self.assertEqual(self.request(CONTENT_LENGTH=str(6 * 1024 * 1024)).status_code, 413)
        self.assertEqual(self.request(CONTENT_LENGTH='bad').status_code, 400)
        self.assertEqual(self.request('/api/products/?q=' + 'x' * 8193).status_code, 414)

    def test_parallel_requests_share_atomic_counter(self):
        with ThreadPoolExecutor(max_workers=8) as workers:
            responses = list(workers.map(lambda _: self.request().status_code, range(20)))
        self.assertEqual(responses.count(200), 4)
        self.assertEqual(responses.count(429), 16)

    def test_cache_outage_is_controlled(self):
        with patch.object(caches['security'], 'add', side_effect=RuntimeError):
            self.assertEqual(self.request().status_code, 503)


class SpreadsheetTests(SimpleTestCase):
    def test_untrusted_formula_is_literal_after_export_and_totals_stay_numeric(self):
        workbook = Workbook()
        workbook.active.append(['=HYPERLINK("https://example.test","click")', 123])
        protect_workbook(workbook)
        stream = BytesIO()
        workbook.save(stream)
        stream.seek(0)
        result = load_workbook(stream)
        self.assertEqual(result.active['A1'].data_type, 's')
        self.assertTrue(result.active['A1'].value.startswith('=HYPERLINK'))
        self.assertEqual(result.active['B1'].value, 123)

    def test_unassigned_or_customer_accounts_cannot_match_unscoped_objects(self):
        permission = IsAdminOrOwnShowroom()
        for role in ('customer', 'showroom_user'):
            request = SimpleNamespace(user=SimpleNamespace(role=role, showroom_id=None))
            self.assertFalse(permission.has_object_permission(request, None, SimpleNamespace(showroom_id=None)))


class AuthenticationRegressionTests(TestCase):
    def test_failed_team_creation_does_not_leave_orphan_login(self):
        from django.db import IntegrityError
        from apps.ecommerce.serializers import TeamSerializer
        serializer = TeamSerializer(data={'username': 'new-team-user', 'password': 'Copper#Lake$947',
                                          'name': 'Team member', 'access_role': 'viewer'})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch('apps.ecommerce.serializers.TeamMember.objects.create', side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                serializer.save()
        self.assertFalse(User.objects.filter(username='new-team-user').exists())

    def test_password_change_revokes_existing_refresh_tokens(self):
        from apps.showrooms.models import Showroom
        showroom = Showroom.objects.create(name='Password test showroom')
        user = User.objects.create_user('password-owner', password='Old-Password#842', role='showroom_user', showroom=showroom)
        token = RefreshToken.for_user(user)
        client = APIClient()
        client.force_authenticate(user)
        response = client.post('/api/accounts/password/change/', {
            'current_password': 'Old-Password#842', 'new_password': 'Cobalt*Mint#962',
            'confirm_password': 'Cobalt*Mint#962'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        user.refresh_from_db()
        self.assertTrue(user.check_password('Cobalt*Mint#962'))
        with self.assertRaises(TokenError):
            RefreshToken(str(token))

    def test_sql_payload_does_not_authenticate_or_modify_users(self):
        User.objects.create_user('admin-safe', password='Safe-Password#833', role='admin')
        client = APIClient()
        response = client.post('/api/auth/login/', {'username': "' OR 1=1; DROP TABLE accounts_user; --", 'password': 'anything'}, format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(User.objects.count(), 1)

    def test_malformed_database_filter_is_not_a_server_error(self):
        user = User.objects.create_user('filter-admin', role='admin')
        client = APIClient()
        client.force_authenticate(user)
        response = client.get('/api/inventory/stocks/', {'showroom': "1 OR 1=1"})
        self.assertEqual(response.status_code, 400, response.data)

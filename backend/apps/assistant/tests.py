import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .views import AssistantAPIException, _groq_chat, _make_plan


class AssistantEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("assistant-chat")

    def test_assistant_is_admin_only(self):
        self.client.force_authenticate(user=SimpleNamespace(
            pk=12, is_authenticated=True, role="showroom_user",
        ))

        response = self.client.post(self.url, {"question": "Showroom sales koto?"}, format="json")

        self.assertEqual(response.status_code, 403)

    @override_settings(GROQ_API_KEY="")
    def test_admin_gets_actionable_error_when_groq_key_is_not_configured(self):
        self.client.force_authenticate(user=SimpleNamespace(
            pk=1, is_authenticated=True, role="admin",
        ))

        response = self.client.post(self.url, {"question": "32 number lot er operator ke?"}, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertIn("GROQ_API_KEY", response.json()["detail"])

    def test_question_is_required_before_calling_groq(self):
        self.client.force_authenticate(user=SimpleNamespace(
            pk=1, is_authenticated=True, role="admin",
        ))

        with patch("apps.assistant.views._groq_chat") as groq_chat:
            response = self.client.post(self.url, {"question": "  "}, format="json")

        self.assertEqual(response.status_code, 400)
        groq_chat.assert_not_called()

    @override_settings(GROQ_API_KEY="test-key")
    @patch("apps.assistant.views._lookup_data", return_value={"lots": [{"operator__name": "Mahmud"}]})
    @patch("apps.assistant.views._make_plan", return_value={"intent": "lot_lookup"})
    @patch("apps.assistant.views._groq_chat", return_value="Lot 32-er operator Mahmud.")
    def test_admin_receives_grounded_answer(self, groq_chat, _make_plan, _lookup_data):
        self.client.force_authenticate(user=SimpleNamespace(
            pk=1, is_authenticated=True, role="admin",
        ))

        response = self.client.post(self.url, {"question": "32 number lot er operator ke?"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"answer": "Lot 32-er operator Mahmud."})
        groq_chat.assert_called_once()

    @patch("apps.assistant.views._groq_chat", return_value='{"intent":"sql_query","date":"2026-01-01"}')
    def test_planner_rejects_intents_outside_the_allowlist(self, _groq_chat):
        self.assertEqual(_make_plan("run any query"), {"intent": "unknown"})


class GroqErrorHandlingTests(SimpleTestCase):
    @override_settings(GROQ_API_KEY="test-groq-key")
    @patch("apps.assistant.views.urlopen")
    def test_invalid_key_returns_safe_configuration_guidance(self, mock_urlopen):
        provider_body = json.dumps({
            "error": {"message": "Invalid key test-groq-key"},
        }).encode("utf-8")
        mock_urlopen.side_effect = HTTPError(
            "https://api.groq.com/", 401, "Unauthorized", {}, BytesIO(provider_body),
        )

        with self.assertRaises(AssistantAPIException) as raised:
            _groq_chat([{"role": "user", "content": "hello"}])

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("GROQ_API_KEY", str(raised.exception.detail))
        self.assertNotIn("test-groq-key", str(raised.exception.detail))

    @override_settings(GROQ_API_KEY="test-groq-key")
    @patch("apps.assistant.views.urlopen")
    def test_unavailable_model_returns_model_configuration_guidance(self, mock_urlopen):
        provider_body = json.dumps({
            "error": {"message": "model not found"},
        }).encode("utf-8")
        mock_urlopen.side_effect = HTTPError(
            "https://api.groq.com/", 404, "Not Found", {}, BytesIO(provider_body),
        )

        with self.assertRaises(AssistantAPIException) as raised:
            _groq_chat([{"role": "user", "content": "hello"}])

        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("GROQ_MODEL", str(raised.exception.detail))
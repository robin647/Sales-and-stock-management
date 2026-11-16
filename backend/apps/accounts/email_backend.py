"""Gmail API transport over HTTPS, including on hosts that block SMTP."""
import base64
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class GmailApiEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        messages = list(email_messages or [])
        if not messages:
            return 0
        values = (settings.GMAIL_CLIENT_ID, settings.GMAIL_CLIENT_SECRET, settings.GMAIL_REFRESH_TOKEN)
        if not all(values):
            raise ImproperlyConfigured("Gmail sender authorization has not been configured.")
        token_request = Request("https://oauth2.googleapis.com/token", data=urlencode({
            "client_id": values[0], "client_secret": values[1], "refresh_token": values[2],
            "grant_type": "refresh_token",
        }).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        with urlopen(token_request, timeout=settings.EMAIL_TIMEOUT) as response:
            token = json.load(response)["access_token"]
        sent = 0
        for message in messages:
            request = Request("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", data=json.dumps({
                "raw": base64.urlsafe_b64encode(message.message().as_bytes()).decode(),
            }).encode(), headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"}, method="POST")
            try:
                with urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:
                    json.load(response)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

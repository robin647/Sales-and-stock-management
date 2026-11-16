from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.core.validators import validate_email


class Command(BaseCommand):
    help = "Check mail configuration without printing secrets. Optionally send a test email."

    def add_arguments(self, parser):
        parser.add_argument("--send-test-to", default="")

    def handle(self, *args, **options):
        backend = settings.EMAIL_BACKEND
        self.stdout.write(f"Email backend: {backend}")
        if backend.endswith("GmailApiEmailBackend"):
            required = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"]
        elif backend.endswith("smtp.EmailBackend"):
            required = ["EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"]
        else:
            required = []
        missing = [key for key in required if not getattr(settings, key, "")]
        if missing:
            raise CommandError("Missing configuration: " + ", ".join(missing) + ". See README.md Gmail setup.")
        self.stdout.write("Required settings are present. Credential validity is not yet tested.")
        recipient = options["send_test_to"]
        if recipient:
            validate_email(recipient)
            try:
                count = send_mail("Mahir Sherwani email delivery test", "Your store can send email using the configured Gmail service.", settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
            except Exception as exc:
                raise CommandError("Email test failed (" + type(exc).__name__ + "). Check credentials, Gmail authorization and hosting restrictions.") from None
            if count != 1:
                raise CommandError("The email transport did not accept the test email.")
            self.stdout.write(self.style.SUCCESS("Test email accepted by the mail service. Check Inbox and Spam."))

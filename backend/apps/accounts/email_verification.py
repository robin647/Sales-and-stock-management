import logging
import secrets
from datetime import timedelta
from uuid import uuid4
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework.exceptions import APIException, ValidationError, Throttled
from .models import User, EmailVerification, OtpSendBudget

logger = logging.getLogger(__name__)
TTL = 60
MAX_ATTEMPTS = 5


class EmailUnavailable(APIException):
    status_code = 503
    default_detail = "Verification email could not be sent. Please contact the store or try again later."


def normalize_email(email):
    return email.strip().casefold()


def code_digest(email, purpose, nonce, code):
    return salted_hmac("customer-email-otp", f"{email}:{purpose}:{nonce}:{code}", algorithm="sha256").hexdigest()


def eligible(email, purpose):
    users = User.objects.filter(email__iexact=email)
    if purpose == "signup" and users.exists():
        raise ValidationError({"email": "An account already uses this email. Sign in or verify your existing account."})
    if purpose == "verify":
        matches = list(users.filter(role="customer", is_active=True)[:2])
        if len(matches) != 1:
            raise ValidationError({"email": "A unique active customer account could not be found. Please contact the store."})
        if matches[0].email_verified:
            raise ValidationError({"email": "This email is already verified. Sign in with your email and password."})


def request_code(email, purpose):
    email = normalize_email(email)
    eligible(email, purpose)
    now = timezone.now()
    nonce = secrets.token_hex(16)
    code = f"{secrets.randbelow(1_000_000):06d}"
    digest = code_digest(email, purpose, nonce, code)
    with transaction.atomic():
        row, created = EmailVerification.objects.get_or_create(email=email, defaults={
            "purpose": purpose, "nonce": nonce, "code_hash": digest, "expires_at": now,
            "sent_at": now, "window_started_at": now,
        })
        row = EmailVerification.objects.select_for_update().get(pk=row.pk)
        if not created and (now - row.sent_at).total_seconds() < TTL:
            raise Throttled(wait=TTL - int((now - row.sent_at).total_seconds()), detail="Wait one minute before requesting another code.")
        if (now - row.window_started_at).total_seconds() >= 3600:
            row.window_started_at = now
            row.sent_count = 0
        if row.sent_count >= 5:
            raise Throttled(wait=3600, detail="Too many codes requested for this email. Please try again later.")
        budget, _ = OtpSendBudget.objects.get_or_create(day=timezone.localdate())
        budget = OtpSendBudget.objects.select_for_update().get(pk=budget.pk)
        if budget.reserved >= settings.OTP_DAILY_EMAIL_LIMIT:
            raise EmailUnavailable("The store's daily verification email limit has been reached. Please try tomorrow.")
        budget.reserved += 1
        budget.save(update_fields=["reserved"])
        row.purpose, row.nonce, row.code_hash = purpose, nonce, digest
        row.expires_at, row.sent_at = now, now
        row.ready, row.consumed, row.attempts = False, False, 0
        row.sent_count += 1
        row.save()
    try:
        sent = send_mail("Your Mahir Sherwani verification code", f"Your verification code is {code}.\n\nIt is valid for 1 minute and can be used once. Never share it with anyone.\nIf you did not request this code, ignore this email.", settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        if sent != 1:
            raise RuntimeError("Email transport did not accept the message")
    except Exception as error:
        logger.warning("Customer verification email failed: %s", type(error).__name__)
        EmailVerification.objects.filter(pk=row.pk, nonce=nonce).update(ready=False)
        raise EmailUnavailable() from None
    expires = timezone.now() + timedelta(seconds=TTL)
    EmailVerification.objects.filter(pk=row.pk, nonce=nonce).update(ready=True, sent_at=timezone.now(), expires_at=expires)
    return {"detail": "A six-digit verification code has been sent to your email.", "expires_at": expires, "expires_in": TTL, "resend_after": TTL}


def consume_code(*, email, purpose, code, signup=None):
    email = normalize_email(email)
    error = None
    user = None
    with transaction.atomic():
        row = EmailVerification.objects.select_for_update().filter(email=email, purpose=purpose).first()
        if not row or not row.ready or row.consumed:
            error = "Request a new verification code for this email."
        elif row.expires_at <= timezone.now():
            error = "This verification code has expired. Request a new code."
        elif row.attempts >= MAX_ATTEMPTS:
            error = "Too many incorrect attempts. Request a new code."
        elif not constant_time_compare(row.code_hash, code_digest(email, purpose, row.nonce, code)):
            row.attempts += 1
            row.save(update_fields=["attempts"])
            error = "The verification code is incorrect."
        else:
            eligible(email, purpose)
            if purpose == "signup":
                first, _, last = signup["name"].partition(" ")
                user = User.objects.create_user(username="customer-" + uuid4().hex, email=email,
                    password=signup["password"], first_name=first, last_name=last,
                    phone_number=signup.get("phone_number", ""), role="customer", email_verified=True)
            else:
                user = User.objects.get(email__iexact=email, role="customer", is_active=True)
                user.email_verified = True
                user.save(update_fields=["email_verified"])
            row.consumed = True
            row.save(update_fields=["consumed"])
    # Raise after committing the attempt counter, not from inside the atomic block.
    if error:
        raise ValidationError({"otp": error})
    return user

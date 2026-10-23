from .base import *  # noqa
from django.core.exceptions import ImproperlyConfigured

DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5:
    raise ImproperlyConfigured(
        "Production SECRET_KEY must be at least 50 characters and use at least 5 distinct characters."
    )
if DEBUG:
    raise ImproperlyConfigured("DEBUG must be False in production.")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production ALLOWED_HOSTS must list the API host and cannot contain '*'.")

# --- Security hardening for production ---
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # 7 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

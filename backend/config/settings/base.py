"""
Base settings shared by local.py and production.py.
Nothing environment-specific (DEBUG, ALLOWED_HOSTS, etc.) lives here directly —
those are read from environment variables so the same codebase works
in local development, Docker, and on Render.
"""

import sys
from datetime import timedelta
from pathlib import Path

import environ
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

for env_file in (BASE_DIR.parent / ".env.local", BASE_DIR.parent / ".env", BASE_DIR / ".env"):
    if env_file.is_file():
        environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY", default="unsafe-dev-key-change-me")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",

    "apps.accounts",
    "apps.showrooms",
    "apps.products",
    "apps.inventory",
    "apps.reports",
    "apps.wholesale",
    "apps.employees",
    "apps.assistant",
    "apps.swing",
    "apps.producers",
    "apps.shop",
    "apps.ecommerce",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.ecommerce.middleware.CommerceAuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_USER_MODEL = "accounts.User"

if "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": env.db(
            "DATABASE_URL", default="postgres://placeholder:placeholder@localhost:5432/placeholder"
        ),
    }
    DATABASES["default"].setdefault("CONN_MAX_AGE", env.int("DB_CONN_MAX_AGE", default=60))
    DATABASES["default"].setdefault("CONN_HEALTH_CHECKS", True)
    DATABASES["default"].setdefault("OPTIONS", {}).setdefault("connect_timeout", 10)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "core.permissions.IsStaffUser",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
        "login": "10/minute",
        "signup": "5/hour",
        "email_otp_request": "20/hour",
        "email_otp_verify": "60/hour",
        "password_change": "5/hour",
        "assistant": "20/minute",
    },
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "TOKEN_REFRESH_SERIALIZER": "apps.accounts.serializers.VerifiedCustomerRefreshSerializer",
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("ACCESS_TOKEN_LIFETIME_MINUTES", default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("REFRESH_TOKEN_LIFETIME_DAYS", default=7)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

CORS_ALLOWED_ORIGINS = list(dict.fromkeys(
    origin.strip().rstrip("/")
    for origin in env.list("CORS_ALLOWED_ORIGINS", default=[])
    if origin.strip()
))
VERCEL_FRONTEND_ORIGIN = "https://sales-and-stock-management-s7d7.vercel.app"
if VERCEL_FRONTEND_ORIGIN not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(VERCEL_FRONTEND_ORIGIN)
CORS_ALLOW_HEADERS = (*default_headers, "idempotency-key")

# Gmail API uses HTTPS and works on hosting plans that block outbound SMTP.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="apps.accounts.email_backend.GmailApiEmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Mahir Sherwani <mhrobin471@gmail.com>")
GMAIL_CLIENT_ID = env("GMAIL_CLIENT_ID", default="")
GMAIL_CLIENT_SECRET = env("GMAIL_CLIENT_SECRET", default="")
GMAIL_REFRESH_TOKEN = env("GMAIL_REFRESH_TOKEN", default="")
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=15)
OTP_DAILY_EMAIL_LIMIT = env.int("OTP_DAILY_EMAIL_LIMIT", default=400)
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="mhrobin471@gmail.com")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

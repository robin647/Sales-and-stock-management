"""Explicit PostgreSQL test configuration; never falls back to production DB."""
from .base import *  # noqa

DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DATABASES = {"default": env.db("TEST_DATABASE_URL")}

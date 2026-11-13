from .base import *  # noqa

LOCAL_DATABASE_URL = env("LOCAL_DATABASE_URL", default="").strip()
if LOCAL_DATABASE_URL and "test" not in sys.argv:
	DATABASES["default"] = env.db_url("LOCAL_DATABASE_URL")
	DATABASES["default"].setdefault("CONN_MAX_AGE", env.int("DB_CONN_MAX_AGE", default=60))
	DATABASES["default"].setdefault("CONN_HEALTH_CHECKS", True)
	DATABASES["default"].setdefault("OPTIONS", {}).setdefault("connect_timeout", 10)

DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

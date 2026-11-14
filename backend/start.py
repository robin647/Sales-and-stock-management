"""Apply schema changes before accepting API traffic on Render or Docker."""

import os
from pathlib import Path
import subprocess
import sys


def repair_legacy_inventory_if_needed():
    import django
    django.setup()
    from django.db import connection
    from django.db.migrations.loader import MigrationLoader
    from apps.inventory.management.commands.repair_legacy_inventory import LEGACY, TARGET

    loader = MigrationLoader(connection)
    if LEGACY not in loader.applied_migrations or TARGET in loader.applied_migrations:
        return
    print("Known legacy inventory migration detected; validating and repairing schema.", flush=True)
    # These migrations are independent of the colliding inventory migration.
    for app in ("accounts", "products", "showrooms"):
        subprocess.run([sys.executable, "manage.py", "migrate", app, "--noinput"], check=True)
    subprocess.run([sys.executable, "manage.py", "repair_legacy_inventory"], check=True)
    connection.close()


def main():
    os.chdir(Path(__file__).resolve().parent)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    repair_legacy_inventory_if_needed()
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=True)
    subprocess.run([sys.executable, "manage.py", "migrate", "--check"], check=True)
    os.execvp("gunicorn", [
        "gunicorn", "config.wsgi:application",
        "--bind", f"0.0.0.0:{os.environ.get('PORT', '8000')}",
        "--worker-class", "gthread", "--workers", os.environ.get("GUNICORN_WORKERS", "1"), "--threads", "4",
        "--timeout", "60", "--max-requests", "1000",
        "--max-requests-jitter", "100",
    ])


if __name__ == "__main__":
    main()

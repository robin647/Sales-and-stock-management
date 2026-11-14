"""Apply schema changes before accepting API traffic on Render or Docker."""

import os
from pathlib import Path
import subprocess
import sys


def main():
    os.chdir(Path(__file__).resolve().parent)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=True)
    subprocess.run([sys.executable, "manage.py", "migrate", "--check"], check=True)
    os.execvp("gunicorn", [
        "gunicorn", "config.wsgi:application",
        "--bind", f"0.0.0.0:{os.environ.get('PORT', '8000')}",
        "--worker-class", "gthread", "--workers", "3", "--threads", "4",
        "--timeout", "60", "--max-requests", "1000",
        "--max-requests-jitter", "100",
    ])


if __name__ == "__main__":
    main()

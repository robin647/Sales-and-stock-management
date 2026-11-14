import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase


class CorsEnvironmentTests(SimpleTestCase):
    def test_trailing_slashes_are_normalized_before_django_checks(self):
        environment = os.environ.copy()
        environment.update({
            "DJANGO_SETTINGS_MODULE": "config.settings.base",
            "CORS_ALLOWED_ORIGINS": "https://sales-and-stock-management-s7d7.vercel.app/, https://shop.example.com///,https://shop.example.com/",
        })
        result = subprocess.run(
            [sys.executable, "-c", "import django; django.setup(); from django.conf import settings; from django.core.checks import run_checks; assert settings.CORS_ALLOWED_ORIGINS == ['https://sales-and-stock-management-s7d7.vercel.app', 'https://shop.example.com']; assert not [e for e in run_checks() if e.id.startswith('corsheaders.')]; print('CORS checks passed')"],
            cwd=Path(__file__).resolve().parent.parent,
            env=environment, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

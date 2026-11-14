import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

import start
from apps.inventory.management.commands.repair_legacy_inventory import LEGACY, TARGET


class StartupTests(SimpleTestCase):
    def test_legacy_database_repairs_before_full_migration(self):
        with patch("django.setup"), patch("django.db.migrations.loader.MigrationLoader", return_value=SimpleNamespace(applied_migrations={LEGACY})), patch("start.subprocess.run") as run, patch("django.db.connection.close"):
            start.repair_legacy_inventory_if_needed()
        self.assertEqual([call.args[0][2:] for call in run.call_args_list], [
            ["migrate", "accounts", "--noinput"],
            ["migrate", "products", "--noinput"],
            ["migrate", "showrooms", "--noinput"],
            ["repair_legacy_inventory"],
        ])
        self.assertTrue(all(call.kwargs["check"] for call in run.call_args_list))

    def test_fresh_and_repaired_databases_skip_legacy_repair(self):
        for applied in (set(), {LEGACY, TARGET}):
            with self.subTest(applied=applied), patch("django.setup"), patch("django.db.migrations.loader.MigrationLoader", return_value=SimpleNamespace(applied_migrations=applied)), patch("start.subprocess.run") as run:
                start.repair_legacy_inventory_if_needed()
                run.assert_not_called()

    def test_migration_failure_prevents_server_start(self):
        with patch("start.os.chdir"), patch("start.repair_legacy_inventory_if_needed"), patch("start.subprocess.run", side_effect=subprocess.CalledProcessError(1, "migrate")), patch("start.os.execvp") as launch:
            with self.assertRaises(subprocess.CalledProcessError):
                start.main()
            launch.assert_not_called()

    def test_successful_start_checks_migrations_and_uses_render_port(self):
        with patch("start.os.chdir"), patch("start.repair_legacy_inventory_if_needed"), patch("start.subprocess.run") as run, patch.dict("start.os.environ", {"PORT": "10000"}), patch("start.os.execvp") as launch:
            start.main()
        self.assertEqual([call.args[0] for call in run.call_args_list], [
            [sys.executable, "manage.py", "migrate", "--noinput"],
            [sys.executable, "manage.py", "migrate", "--check"],
        ])
        self.assertIn("0.0.0.0:10000", launch.call_args.args[1])

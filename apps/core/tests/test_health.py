from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.core.models import Schedule

User = get_user_model()


class TestHealthApi(TestCase):
    def setUp(self):
        self.crontab_directory = TemporaryDirectory()
        self.addCleanup(self.crontab_directory.cleanup)
        self.settings_override = override_settings(CRONTAB_PATH=Path(self.crontab_directory.name))
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    @patch("apps.core.health.shutil.disk_usage")
    @patch("apps.core.health.process_is_running", side_effect=[True, True])
    def test_healthy_system_returns_ok(self, _process_is_running, disk_usage):
        disk_usage.return_value = Mock(total=1000, used=799)

        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertEqual(response.json()["checks"]["cron"]["status"], "healthy")
        self.assertTrue(response.json()["checks"]["cron"]["running"])
        self.assertEqual(response.json()["checks"]["cron_files"]["status"], "healthy")
        self.assertEqual(response.json()["checks"]["cron_files"]["missing_files"], [])
        self.assertEqual(response.json()["checks"]["job_updater"]["status"], "healthy")
        self.assertTrue(response.json()["checks"]["job_updater"]["running"])
        self.assertEqual(response.json()["checks"]["disk"]["status"], "healthy")
        self.assertEqual(response.json()["checks"]["disk"]["used_percent"], 79.9)

    @patch("apps.core.health.shutil.disk_usage")
    @patch("apps.core.health.process_is_running", side_effect=[True, False])
    def test_unhealthy_system_returns_check_statuses(self, _process_is_running, disk_usage):
        disk_usage.return_value = Mock(total=1000, used=800)

        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unhealthy")
        self.assertEqual(response.json()["checks"]["cron"]["status"], "healthy")
        self.assertEqual(response.json()["checks"]["job_updater"]["status"], "unhealthy")
        self.assertEqual(response.json()["checks"]["disk"]["status"], "unhealthy")

    @patch("apps.core.health.shutil.disk_usage", side_effect=OSError("disk unavailable"))
    @patch("apps.core.health.process_is_running", side_effect=[True, True])
    def test_disk_check_error_is_reported_as_unhealthy(self, _process_is_running, _disk_usage):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"]["disk"]["status"], "unhealthy")
        self.assertEqual(response.json()["checks"]["disk"]["error"], "disk unavailable")

    @patch("apps.core.health.shutil.disk_usage")
    @patch("apps.core.health.process_is_running", side_effect=[True, True])
    def test_missing_cron_files_are_listed_as_unhealthy(self, _process_is_running, disk_usage):
        disk_usage.return_value = Mock(total=1000, used=100)
        present_schedule = Schedule.objects.create(name="present", image="alpine", cron_rule="0 0 * * *")
        missing_schedule = Schedule.objects.create(name="missing", image="alpine", cron_rule="0 1 * * *")
        (Path(self.crontab_directory.name) / f"ct_{present_schedule.id}").touch()

        response = self.client.get("/api/health/")

        cron_files = response.json()["checks"]["cron_files"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unhealthy")
        self.assertEqual(cron_files["status"], "unhealthy")
        self.assertEqual(cron_files["expected_count"], 2)
        self.assertEqual(cron_files["missing_files"], [f"ct_{missing_schedule.id}"])


class TestCronFilesRepairApi(TestCase):
    def setUp(self):
        self.crontab_directory = TemporaryDirectory()
        self.addCleanup(self.crontab_directory.cleanup)
        self.settings_override = override_settings(CRONTAB_PATH=Path(self.crontab_directory.name))
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.user = User.objects.create_user(username="operator", password="testpassword")
        self.client.force_login(self.user)

    def test_recreates_only_missing_schedule_files(self):
        existing_schedule = Schedule.objects.create(name="existing", image="alpine", cron_rule="0 0 * * *")
        missing_schedule = Schedule.objects.create(name="missing", image="alpine", cron_rule="0 1 * * *")
        existing_path = settings.CRONTAB_PATH / f"ct_{existing_schedule.id}"
        existing_path.write_text("leave this definition unchanged\n", encoding="utf-8")

        response = self.client.post("/api/health/cron-files/recreate/")

        missing_filename = f"ct_{missing_schedule.id}"
        missing_path = settings.CRONTAB_PATH / missing_filename
        expected_command = settings.CRONJOB_CMD.format(
            schedule_id=missing_schedule.id,
            cron_rule=missing_schedule.cron_rule,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recreated_count"], 1)
        self.assertEqual(response.json()["recreated_files"], [missing_filename])
        self.assertTrue(response.json()["health"]["checks"]["cron_files"]["healthy"])
        self.assertEqual(existing_path.read_text(encoding="utf-8"), "leave this definition unchanged\n")
        self.assertEqual(missing_path.read_text(encoding="utf-8"), f"{expected_command}\n")

    def test_repair_is_idempotent(self):
        schedule = Schedule.objects.create(name="missing", image="alpine", cron_rule="0 0 * * *")

        first_response = self.client.post("/api/health/cron-files/recreate/")
        second_response = self.client.post("/api/health/cron-files/recreate/")

        self.assertEqual(first_response.json()["recreated_count"], 1)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.json()["recreated_count"], 0)
        self.assertEqual(second_response.json()["recreated_files"], [])
        self.assertTrue((settings.CRONTAB_PATH / f"ct_{schedule.id}").is_file())

    def test_repair_requires_authentication(self):
        schedule = Schedule.objects.create(name="missing", image="alpine", cron_rule="0 0 * * *")
        self.client.logout()

        response = self.client.post("/api/health/cron-files/recreate/")

        self.assertEqual(response.status_code, 403)
        self.assertFalse((settings.CRONTAB_PATH / f"ct_{schedule.id}").exists())

    @patch("apps.core.health.write_crontab", side_effect=OSError("read-only filesystem"))
    def test_write_error_returns_server_error(self, _write_crontab):
        Schedule.objects.create(name="missing", image="alpine", cron_rule="0 0 * * *")

        response = self.client.post("/api/health/cron-files/recreate/")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Unable to recreate missing schedule files.")

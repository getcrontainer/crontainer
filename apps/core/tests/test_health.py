from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from apps.core.models import Schedule


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

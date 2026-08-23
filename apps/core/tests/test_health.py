from unittest.mock import Mock, patch

from django.test import SimpleTestCase


class TestHealthApi(SimpleTestCase):
    @patch("apps.core.health.shutil.disk_usage")
    @patch("apps.core.health.process_is_running", side_effect=[True, True])
    def test_healthy_system_returns_ok(self, _process_is_running, disk_usage):
        disk_usage.return_value = Mock(total=1000, used=799)

        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertEqual(response.json()["checks"]["cron"]["status"], "healthy")
        self.assertTrue(response.json()["checks"]["cron"]["running"])
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

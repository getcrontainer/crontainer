from io import StringIO
from unittest.mock import Mock, patch

from django.test import TestCase

from apps.core.management.commands.update_history import MISSING_CONTAINER_STATUS_CODE, Command
from apps.core.models import Job, Schedule


class TestUpdateHistory(TestCase):
    def setUp(self):
        self.schedule = Schedule.objects.create(name="history", image="alpine", cron_rule="* * * * *")

    def command(self):
        return Command(stdout=StringIO(), stderr=StringIO())

    @patch.object(Command, "_check_container", return_value=None)
    def test_missing_container_marks_job_as_terminal_failure(self, _check_container):
        job = Job.objects.create(schedule=self.schedule, provisioning=False)

        self.command()._update_job(job)

        job.refresh_from_db()
        self.assertEqual(job.status, "failure")
        self.assertEqual(job.status_code, MISSING_CONTAINER_STATUS_CODE)
        self.assertEqual(job.state["Status"], "missing")
        self.assertIn(str(job.id), job.log)
        self.assertFalse(Job.objects.filter(id=job.id, status_code__isnull=True).exists())

    @patch.object(Command, "_check_container")
    def test_exited_container_persists_result_and_is_removed(self, check_container):
        job = Job.objects.create(schedule=self.schedule, provisioning=False)
        container = Mock(
            status="exited",
            attrs={"State": {"Status": "exited", "StartedAt": "2026-01-01T00:00:00Z"}},
        )
        container.logs.return_value = b"finished\n"
        container.wait.return_value = {"StatusCode": 0}
        check_container.return_value = container

        self.command()._update_job(job)

        job.refresh_from_db()
        self.assertEqual(job.status, "exited")
        self.assertEqual(job.status_code, 0)
        self.assertEqual(job.log, "finished\n")
        self.assertEqual(job.state["Status"], "exited")
        container.remove.assert_called_once_with()

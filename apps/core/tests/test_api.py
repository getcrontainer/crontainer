import shutil
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Credential, Job, Schedule
from apps.node.models import Node

User = get_user_model()


class ApiTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.client.force_login(self.user)
        shutil.rmtree(settings.CRONTAB_PATH, ignore_errors=True)
        settings.CRONTAB_PATH.mkdir(parents=True)


class TestScheduleApi(ApiTestCase):
    def test_create_list_update_and_delete_schedule(self):
        response = self.client.post(
            "/api/schedules/",
            data={"name": "nightly", "image": "alpine:latest", "cron_rule": "0 0 * * *", "env_vars": {"MODE": "night"}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        schedule_id = response.json()["id"]
        self.assertEqual(response.json()["created_by"], "testuser")
        self.assertEqual(response.json()["success_rate"], 0.0)
        self.assertTrue((settings.CRONTAB_PATH / f"ct_{schedule_id}").exists())

        response = self.client.get("/api/schedules/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["name"], "nightly")

        response = self.client.patch(
            f"/api/schedules/{schedule_id}/",
            data={"active": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["active"])

        response = self.client.delete(f"/api/schedules/{schedule_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Schedule.objects.filter(id=schedule_id).exists())
        self.assertFalse((settings.CRONTAB_PATH / f"ct_{schedule_id}").exists())

    def test_invalid_cron_rule_is_rejected(self):
        for cron_rule in ["invalid", "/5 0 * * *"]:
            with self.subTest(cron_rule=cron_rule):
                response = self.client.post(
                    "/api/schedules/",
                    data={"name": "invalid", "image": "alpine", "cron_rule": cron_rule},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("cron_rule", response.json())

    def test_success_rate_uses_the_latest_1000_completed_executions(self):
        schedule = Schedule.objects.create(
            name="measured",
            image="alpine:latest",
            cron_rule="0 0 * * *",
            created_by=self.user,
        )
        now = timezone.now()
        jobs = [
            Job(schedule=schedule, status="exited", status_code=0, created_at=now - timedelta(seconds=1002)),
            Job(schedule=schedule, status="exited", status_code=0, created_at=now - timedelta(seconds=1001)),
        ]
        jobs.extend(
            Job(
                schedule=schedule,
                status="exited",
                status_code=0 if index < 250 else 1,
                created_at=now - timedelta(seconds=1000 - index),
            )
            for index in range(1000)
        )
        Job.objects.bulk_create(jobs)
        Job.objects.create(schedule=schedule, status="running", status_code=None, created_at=now + timedelta(seconds=1))

        response = self.client.get(f"/api/schedules/{schedule.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["success_rate"], 25.0)


class TestCredentialApi(ApiTestCase):
    def test_password_is_required_on_create_and_never_returned(self):
        response = self.client.post("/api/credentials/", data={"name": "hub"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/credentials/",
            data={"name": "hub", "username": "alice", "password": "secret", "category": 1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.json())
        self.assertEqual(response.json()["schedule_count"], 0)
        self.assertEqual(Credential.objects.get(name="hub").password, "secret")


class TestAuthAndUtilityApi(ApiTestCase):
    def test_current_user_and_cron_description(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "testuser")

        response = self.client.get("/api/describe-cron/?cron_rule=*+*+*+*+*")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["description"], "Every minute")

        response = self.client.get("/api/describe-cron/?cron_rule=%2F5+0+*+*+*")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["description"], "Invalid cron expression")


class TestPagination(ApiTestCase):
    def test_all_resource_lists_use_standard_pagination(self):
        for endpoint in ["schedules", "jobs", "credentials", "users", "nodes"]:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f"/api/{endpoint}/")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.json()), {"count", "next", "previous", "results"})

    def test_resource_pages_contain_at_most_50_items(self):
        Credential.objects.bulk_create(Credential(name=f"credential-{index}", password="secret") for index in range(51))

        first_page = self.client.get("/api/credentials/")
        second_page = self.client.get("/api/credentials/?page=2")

        self.assertEqual(first_page.json()["count"], 51)
        self.assertEqual(len(first_page.json()["results"]), 50)
        self.assertIsNotNone(first_page.json()["next"])
        self.assertEqual(len(second_page.json()["results"]), 1)
        self.assertIsNotNone(second_page.json()["previous"])

    def test_dashboard_summary_uses_all_records(self):
        active_schedule = Schedule.objects.create(name="active", image="alpine", cron_rule="0 0 * * *")
        Schedule.objects.create(name="paused", image="alpine", cron_rule="0 1 * * *", active=False)
        Job.objects.create(schedule=active_schedule, status="exited", status_code=0)
        Job.objects.create(schedule=active_schedule, status="failure", status_code=1)
        Credential.objects.bulk_create(Credential(name=f"registry-{index}", password="secret") for index in range(51))
        Node.objects.create(name="ssh", host="ssh.internal", port=22, use_ssh=True)
        Node.objects.create(name="direct", host="docker.internal", port=2375, use_ssh=False)
        User.objects.create_superuser(username="admin", password="admin-password")

        response = self.client.get("/api/dashboard/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["schedules"], {"total": 2, "active": 1})
        self.assertEqual(response.json()["jobs"], {"total": 2, "healthy": 1})
        self.assertEqual(response.json()["credentials"], {"total": 51})
        self.assertEqual(response.json()["nodes"], {"total": 2, "ssh": 1})
        self.assertEqual(response.json()["users"], {"total": 2, "administrators": 1})

import shutil
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

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
    def test_schedule_defaults_to_the_local_node_and_rejects_null(self):
        node = Node.objects.create(
            name="local",
            host="localhost",
            unix_socket="/var/run/docker.sock",
        )
        response = self.client.post(
            "/api/schedules/",
            data={"name": "nightly", "image": "alpine:latest", "cron_rule": "0 0 * * *"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["node"], str(node.id))
        self.assertEqual(response.json()["node_name"], "local")

        response = self.client.patch(
            f"/api/schedules/{response.json()['id']}/",
            data={"node": None},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["node"], ["This field may not be null."])

    def test_create_list_update_and_delete_schedule(self):
        primary_node = Node.objects.create(
            name="primary",
            host="primary.internal",
            unix_socket="/var/run/docker-primary.sock",
        )
        fallback_node = Node.objects.create(
            name="fallback",
            host="fallback.internal",
            unix_socket="/var/run/docker-fallback.sock",
        )
        response = self.client.post(
            "/api/schedules/",
            data={
                "name": "nightly",
                "image": "alpine:latest",
                "cron_rule": "0 0 * * *",
                "env_vars": {"MODE": "night"},
                "node": str(primary_node.id),
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        schedule_id = response.json()["id"]
        self.assertEqual(response.json()["created_by"], "testuser")
        self.assertEqual(response.json()["success_rate"], 0.0)
        self.assertEqual(response.json()["node"], str(primary_node.id))
        self.assertEqual(response.json()["node_name"], "primary")
        self.assertTrue((settings.CRONTAB_PATH / f"ct_{schedule_id}").exists())

        response = self.client.get("/api/schedules/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["name"], "nightly")
        self.assertEqual(response.json()["results"][0]["node"], str(primary_node.id))
        self.assertEqual(response.json()["results"][0]["node_name"], "primary")

        response = self.client.patch(
            f"/api/schedules/{schedule_id}/",
            data={"active": False, "node": str(fallback_node.id)},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["active"])
        self.assertEqual(response.json()["node"], str(fallback_node.id))
        self.assertEqual(response.json()["node_name"], "fallback")

        fallback_node.delete()
        response = self.client.get(f"/api/schedules/{schedule_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["node"])
        self.assertIsNone(response.json()["node_name"])

        response = self.client.delete(f"/api/schedules/{schedule_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Schedule.objects.filter(id=schedule_id).exists())
        self.assertFalse((settings.CRONTAB_PATH / f"ct_{schedule_id}").exists())

    def test_invalid_cron_rule_is_rejected(self):
        Node.objects.create(name="local", host="localhost", unix_socket="/var/run/docker.sock")
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


class TestJobApi(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.nightly = Schedule.objects.create(name="nightly", image="alpine", cron_rule="0 0 * * *")
        self.hourly = Schedule.objects.create(name="hourly", image="alpine", cron_rule="0 * * * *")
        self.running_job = Job.objects.create(schedule=self.nightly, status="running")
        self.exited_job = Job.objects.create(schedule=self.nightly, status="exited", status_code=0)
        self.failed_job = Job.objects.create(schedule=self.hourly, status="failure", status_code=-100)

    def test_filters_jobs_by_status(self):
        response = self.client.get("/api/jobs/?status=running")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], str(self.running_job.id))

    def test_filters_jobs_by_schedule(self):
        response = self.client.get(f"/api/jobs/?schedule={self.nightly.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            {job["id"] for job in response.json()["results"]},
            {str(self.running_job.id), str(self.exited_job.id)},
        )

    def test_combines_status_and_schedule_filters(self):
        response = self.client.get(f"/api/jobs/?status=failure&schedule={self.hourly.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], str(self.failed_job.id))

    def test_rejects_invalid_schedule_filter(self):
        response = self.client.get("/api/jobs/?schedule=not-a-uuid")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["schedule"], ["Enter a valid schedule ID."])

    def test_filter_options_include_job_statuses_and_schedules(self):
        unused_schedule = Schedule.objects.create(name="unused", image="alpine", cron_rule="0 2 * * *")

        response = self.client.get("/api/jobs/filter-options/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["statuses"], ["exited", "failure", "running"])
        self.assertEqual(
            response.json()["schedules"],
            [
                {"id": str(self.hourly.id), "name": "hourly"},
                {"id": str(self.nightly.id), "name": "nightly"},
            ],
        )
        self.assertNotIn(str(unused_schedule.id), {item["id"] for item in response.json()["schedules"]})

    def test_filtered_pagination_preserves_query_parameters(self):
        Job.objects.bulk_create(Job(schedule=self.nightly, status="running") for _index in range(50))

        first_response = self.client.get(f"/api/jobs/?status=running&schedule={self.nightly.id}")
        next_url = urlparse(first_response.json()["next"])
        second_response = self.client.get(f"{next_url.path}?{next_url.query}")

        self.assertEqual(first_response.json()["count"], 51)
        self.assertEqual(len(first_response.json()["results"]), 50)
        self.assertEqual(
            parse_qs(next_url.query),
            {"page": ["2"], "schedule": [str(self.nightly.id)], "status": ["running"]},
        )
        self.assertEqual(len(second_response.json()["results"]), 1)


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
        Node.objects.create(name="ssh", host="ssh.internal", port=22, use_ssh=True, unix_socket="/ssh.sock")
        Node.objects.create(
            name="direct",
            host="docker.internal",
            port=2375,
            use_ssh=False,
            unix_socket="/direct.sock",
        )
        User.objects.create_superuser(username="admin", password="admin-password")

        response = self.client.get("/api/dashboard/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["schedules"], {"total": 2, "active": 1})
        self.assertEqual(response.json()["jobs"], {"total": 2, "healthy": 1})
        self.assertEqual(response.json()["credentials"], {"total": 51})
        self.assertEqual(response.json()["nodes"], {"total": 2, "ssh": 1})
        self.assertEqual(response.json()["users"], {"total": 2, "administrators": 1})

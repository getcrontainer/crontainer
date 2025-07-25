from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import Schedule
from apps.core.tests.helpers import EasyResponse, add_default_data

User = get_user_model()


class TestScheduleCreateView(TestCase):
    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.user = User.objects.get(username="testuser")

    def test_get(self):
        self.client.force_login(self.user)
        response = self.client.get("/create/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/schedule_form.html")

    def test_post_empty(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/create/",
            {
                "name": "",
                "cron_rule": "",
                "image": "",
                "credential": "",
                "cmd": "",
                "cpu": "",
                "memory": "",
                "active": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/schedule_form.html")

        view = EasyResponse(response)

        self.assertEqual(
            view.form.errors,
            {
                "name": ["This field is required."],
                "cron_rule": ["This field is required."],
                "image": ["This field is required."],
            },
        )

    def test_post_invalid_cron_rule(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/create/",
            {
                "name": "test",
                "cron_rule": "invalid",
                "image": "test",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/schedule_form.html")

        view = EasyResponse(response)

        self.assertEqual(
            view.form.errors,
            {
                "cron_rule": ["Cronjob expression is composed of 5 elements"],
            },
        )

    def test_post_valid(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/create/",
            {
                "name": "test",
                "cron_rule": "0 0 * * *",
                "image": "test",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/")


class TestScheduleDeleteView(TestCase):
    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.user = User.objects.get(username="testuser")

    def test_post(self):
        self.client.force_login(self.user)
        schedule = Schedule.objects.create(
            name="test",
            cron_rule="0 0 * * *",
            image="test",
        )
        schedule.save()

        response = self.client.post(f"/delete/{schedule.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/")

    def test_post_not_found(self):
        self.client.force_login(self.user)
        response = self.client.post("/delete/999/")
        self.assertEqual(response.status_code, 404)


class TestScheduleListView(TestCase):
    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.user = User.objects.get(username="testuser")

    def test_get_empty(self):
        self.client.force_login(self.user)
        response = self.client.get("/")

        view = EasyResponse(response)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(view.object_list.count(), 0)

    def test_get_with_data(self):
        self.client.force_login(self.user)
        schedule = Schedule.objects.create(
            name="test",
            cron_rule="0 0 * * *",
            image="test",
        )

        schedule.save()

        response = self.client.get("/")

        view = EasyResponse(response)

        self.assertEqual(response.status_code, 200)

        self.assertIn(schedule, view.object_list)

        self.assertEqual(view.object_list.count(), 1)


class TestScheduleEnvVars(TestCase):
    def test_key_starts_with_number(self):
        response = self.client.post(
            "/create/",
            {
                "name": "test",
                "cron_rule": "0 0 * * *",
                "image": "test",
                "env_vars_keys": ["1key"],
                "env_vars_values": ["value"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/schedule_form.html")

        view = EasyResponse(response)

        self.assertEqual(
            view.form.errors,
            {
                "env_vars": ["Invalid environment variable key: '1key'"],
            },
        )

    def test_key_invalid_characters(self):
        response = self.client.post(
            "/create/",
            {
                "name": "test",
                "cron_rule": "0 0 * * *",
                "image": "test",
                "env_vars_keys": ["key!"],
                "env_vars_values": ["value"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/schedule_form.html")

        view = EasyResponse(response)

        self.assertEqual(
            view.form.errors,
            {
                "env_vars": ["Invalid environment variable key: 'key!'"],
            },
        )

    def test_key_empty(self):
        response = self.client.post(
            "/create/",
            {
                "name": "test",
                "cron_rule": "0 0 * * *",
                "image": "test",
                "env_vars_keys": [""],
                "env_vars_values": ["value"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/schedule_form.html")

        view = EasyResponse(response)

        self.assertEqual(
            view.form.errors,
            {
                "env_vars": ["Invalid environment variable key: ''"],
            },
        )

    def test_value_empty(self):
        response = self.client.post(
            "/create/",
            {
                "name": "test",
                "cron_rule": "0 0 * * *",
                "image": "test",
                "env_vars_keys": ["key"],
                "env_vars_values": [""],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/schedule_form.html")

        view = EasyResponse(response)

        self.assertEqual(
            view.form.errors,
            {
                "env_vars": ["Value for environment variable 'key' is required"],
            },
        )

    def test_valid(self):
        response = self.client.post(
            "/create/",
            {
                "name": "test",
                "cron_rule": "0 0 * * *",
                "image": "test",
                "env_vars_keys": ["key"],
                "env_vars_values": ["value"],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/")

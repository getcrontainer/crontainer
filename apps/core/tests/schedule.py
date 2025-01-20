import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import Schedule
from apps.core.tests.helpers import EasyResponse


class TestScheduleCreateView(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.create(username="test", password="test")

    def setUp(self):
        self.client.force_login(self.user)

    def test_get(self):
        response = self.client.get("/create/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/schedule_form.html")

    def test_post_empty(self):
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
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.create(username="test", password="test")

    def setUp(self):
        self.client.force_login(self.user)

    def test_post(self):
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
        response = self.client.post("/delete/999/")
        self.assertEqual(response.status_code, 404)

    def test_unauthorized(self):
        self.client.logout()
        _uuid = uuid.uuid4()
        response = self.client.post(f"/delete/{_uuid}/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"/accounts/login/?next=/delete/{_uuid}/")


class TestScheduleListView(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.create(username="test", password="test")

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_empty(self):
        response = self.client.get("/")

        view = EasyResponse(response)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(view.object_list.count(), 0)

    def test_get_with_data(self):
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

    def test_unauthorized(self):
        self.client.logout()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/accounts/login/?next=/")

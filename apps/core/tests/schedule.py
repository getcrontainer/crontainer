from django.test import TestCase

from apps.core.models import Schedule
from apps.core.tests.helpers import EasyResponse


class TestScheduleCreateView(TestCase):
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


class TestScheduleListView(TestCase):
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

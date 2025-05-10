from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.tests.helpers import add_default_data

User = get_user_model()


class TestDescribeCronView(TestCase):

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.user = User.objects.get(username="testuser")

    def test_describe_cron_every_minute_every_hour_every_day(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("describe_cron"), data={"cron_rule": "* * * * *"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Every minute, every hour, every day")

    def test_describe_cron_should_return_invalid_cron_expression(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("describe_cron"), data={"cron_rule": "some expression"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Invalid cron expression")

    def test_describe_cron_should_fail_when_no_cron_rule_provided(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("describe_cron"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Invalid cron expression")

from django.test import TestCase
from django.urls import reverse


class TestDescribeCronView(TestCase):
    def test_describe_cron_every_minute_every_hour_every_day(self):
        response = self.client.get(reverse("describe_cron"), data={"cron_rule": "* * * * *"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Every minute, every hour, every day")

    def test_describe_cron_should_return_invalid_cron_expression(self):
        response = self.client.get(reverse("describe_cron"), data={"cron_rule": "some expression"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Invalid cron expression")

    def test_describe_cron_should_fail_when_no_cron_rule_provided(self):
        response = self.client.get(reverse("describe_cron"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Invalid cron expression")

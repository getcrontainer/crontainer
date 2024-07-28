import uuid

import dateutil
from django.db import models
from django.db.models import CASCADE
from django.utils import timezone

category_choices = (
    (1, "Dockerhub Token"),
    (2, "Github Private Access Token"),
    (3, "aws ECR (Elastic Container Registry)"),
    (98, "generic git repository"),
    (98, "generic registry"),
    (99, "generic HTTP auth"),
)


class Credential(models.Model):

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, unique=True)
    name = models.SlugField(max_length=50, unique=True)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    category = models.IntegerField(choices=category_choices, default=0)

    def __str__(self):
        return self.name

    def json(self):
        if self.category == 3:
            username = "aws"
            password = "fetch using boto"  # TODO: boto action.
        else:
            username = self.username
            password = self.password

        return {"username": username, "password": password}


class Schedule(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, unique=True)
    name = models.SlugField(max_length=500)
    parameters = models.CharField(blank=True, max_length=500)
    created_by = models.EmailField()
    created_at = models.DateTimeField(default=timezone.now)
    cron_rule = models.CharField(max_length=25)
    cron_rule_hash = models.CharField(max_length=200, blank=True, db_index=True)
    active = models.BooleanField(default=True, help_text="Active")
    singleton = models.BooleanField(
        default=False,
        help_text="Selecting this option will make this schedule a singleton: only one instance will be allowed to run at any given time.",
    )
    sequential_failures = models.IntegerField(default=0)

    env_vars = models.JSONField(null=True, blank=True)
    image = models.CharField(max_length=500, blank=False, verbose_name="Image")
    credential = models.ForeignKey(
        Credential,
        null=True,
        blank=True,
        on_delete=CASCADE,
        help_text="If you leave blank, will assume node default registry.",
        verbose_name="Credentials",
    )

    cpu = models.IntegerField(null=True, blank=True)
    memory = models.IntegerField(null=True, blank=True)


class Job(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, unique=True)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    state = models.JSONField(null=True)
    status = models.CharField(max_length=20, default="waiting")
    created_at = models.DateTimeField(default=timezone.now)
    log = models.TextField(blank=True)
    status_code = models.IntegerField(null=True)
    provisioning = models.BooleanField(default=True)

    exception_on_build = models.BooleanField(default=False)
    exception_on_pull = models.BooleanField(default=False)
    exception_on_run = models.BooleanField(default=False)

    def duration(self):
        if self.status != "exited":
            return "n/a"
        try:
            start = dateutil.parser.parse(self.state["StartedAt"])
            end = dateutil.parser.parse(self.state["FinishedAt"])
            if end.year == 1:
                end = timezone.now()
            return (end - start).seconds
        except TypeError:
            return "n/a"

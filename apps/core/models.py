import uuid

import dateutil
from cron_descriptor import ExpressionDescriptor, FormatException, MissingFieldException, Options as CronOptions
from django.db import models
from django.db.models import PROTECT
from django.utils import timezone

cron_options = CronOptions()

cron_options.verbose = True
cron_options.use_24hour_time_format = True


class CategoryChoices(models.IntegerChoices):
    DOCKERHUB = 1
    GITHUB_PAT = 2
    AWS_ECR = 3
    GITLAB_PAT = 4
    GENERIC_REGISTRY = 97
    GENERIC_GIT = 98
    GENERIC_HTTP_AUTH = 99


class Credential(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, unique=True)
    name = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name="Label",
        help_text="Name of your credential",
    )
    username = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=100)
    category = models.IntegerField(choices=CategoryChoices, default=1, blank=True)

    def __str__(self):
        return str(self.name)

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
    cmd = models.CharField(blank=True, max_length=500, help_text="Command to execute")
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
        on_delete=PROTECT,
        help_text="If you leave blank, will assume node default registry.",
        verbose_name="Credentials",
    )

    cpu = models.IntegerField(null=True, blank=True)
    memory = models.IntegerField(null=True, blank=True)

    def get_source_icon(self):
        return f"mdi mdi-{self.source_name.lower()}"

    @property
    def source_name(self):
        if self.image.startswith("https://github.com"):
            return "GitHub"
        if self.image.startswith("https://gitlab.com"):
            return "GitLab"
        return "Docker"

    @property
    def cron_description(self):
        try:
            return ExpressionDescriptor(self.cron_rule, options=cron_options).get_description()
        except (MissingFieldException, FormatException):
            return "Invalid cron rule"


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
        # pylint: disable=unsubscriptable-object
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


class Node(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, unique=True)
    name = models.CharField(max_length=500)
    host = models.CharField(max_length=250)
    port = models.IntegerField(default=2375)
    use_ssh = models.BooleanField(default=False)
    secret = models.CharField(max_length=500, blank=True)

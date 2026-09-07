"""Serializers for schedules, jobs, credentials, and users."""

from cronsim import CronSimError
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.core.cron import parse_cron_rule
from apps.core.models import Credential, Job, Schedule
from apps.node.models import Node

User = get_user_model()
DEFAULT_NODE_UNIX_SOCKET = "/var/run/docker.sock"


def get_default_node():
    return Node.objects.get(unix_socket=DEFAULT_NODE_UNIX_SOCKET)


def validate_cron_rule(value: str) -> str:
    try:
        parse_cron_rule(value)
    except CronSimError as exc:
        raise serializers.ValidationError(f"Invalid cron expression: {exc}") from exc
    return value


class CredentialSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    schedule_count = serializers.SerializerMethodField()

    class Meta:
        model = Credential
        fields = ["id", "name", "username", "password", "category", "schedule_count"]

    def get_schedule_count(self, credential):
        count = getattr(credential, "schedule_count", None)
        return count if count is not None else credential.schedule_set.count()

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "This field is required."})
        return attrs


class ScheduleSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.username", read_only=True)
    cron_description = serializers.CharField(read_only=True)
    source_name = serializers.CharField(read_only=True)
    credential_name = serializers.CharField(source="credential.name", read_only=True)
    node_name = serializers.CharField(source="node.name", read_only=True, allow_null=True)
    node = serializers.PrimaryKeyRelatedField(
        queryset=Node.objects.all(),
        allow_null=False,
        default=get_default_node,
    )
    cron_rule = serializers.CharField(validators=[validate_cron_rule])
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [
            "id",
            "name",
            "cmd",
            "parameters",
            "created_by",
            "created_at",
            "cron_rule",
            "cron_description",
            "active",
            "singleton",
            "sequential_failures",
            "success_rate",
            "env_vars",
            "image",
            "source_name",
            "credential",
            "credential_name",
            "node",
            "node_name",
            "cpu",
            "memory",
        ]
        read_only_fields = ["id", "created_at", "created_by", "sequential_failures"]

    def get_success_rate(self, schedule):
        executions = getattr(schedule, "recent_executions", None)
        if executions is None:
            executions = list(schedule.job_set.filter(status_code__isnull=False).order_by("-created_at")[:1000])
        if not executions:
            return 0.0
        successful = sum(job.status_code == 0 for job in executions)
        return round((successful / len(executions)) * 100, 2)


class JobSerializer(serializers.ModelSerializer):
    schedule_name = serializers.CharField(source="schedule.name", read_only=True)
    schedule_cron_rule = serializers.CharField(source="schedule.cron_rule", read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id",
            "schedule",
            "schedule_name",
            "schedule_cron_rule",
            "state",
            "status",
            "created_at",
            "log",
            "status_code",
            "provisioning",
            "exception_on_build",
            "exception_on_pull",
            "exception_on_run",
            "duration",
        ]
        read_only_fields = fields

    def get_duration(self, job):
        return job.duration()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "date_joined",
            "last_login",
            "is_superuser",
        ]
        read_only_fields = ["id", "date_joined", "last_login", "is_superuser"]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "This field is required."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

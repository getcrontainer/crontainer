"""JSON API for schedules, jobs, credentials, and user management."""

import os

import cron_descriptor
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db.models import Prefetch
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.core.models import Credential, Job, Schedule

User = get_user_model()


def validate_cron_rule(value: str) -> str:
    if len(value.split()) != 5:
        raise serializers.ValidationError("Cronjob expression is composed of 5 elements.")
    try:
        cron_descriptor.get_description(value)
    except cron_descriptor.Exception.FormatException as exc:
        raise serializers.ValidationError("Not a valid cronjob expression.") from exc
    return value


def write_crontab(schedule: Schedule) -> None:
    command = settings.CRONJOB_CMD.format(schedule_id=schedule.id, cron_rule=schedule.cron_rule)
    settings.CRONTAB_PATH.mkdir(parents=True, exist_ok=True)
    (settings.CRONTAB_PATH / f"ct_{schedule.id}").write_text(f"{command}\n", encoding="utf-8")


class CredentialSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Credential
        fields = ["id", "name", "username", "password", "category"]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "This field is required."})
        return attrs


class ScheduleSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.username", read_only=True)
    cron_description = serializers.CharField(read_only=True)
    source_name = serializers.CharField(read_only=True)
    credential_name = serializers.CharField(source="credential.name", read_only=True)
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


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = (
        Schedule.objects.select_related("credential", "created_by")
        .prefetch_related(
            Prefetch(
                "job_set",
                queryset=Job.objects.filter(status_code__isnull=False).order_by("-created_at")[:1000],
                to_attr="recent_executions",
            )
        )
        .order_by("name")
    )
    serializer_class = ScheduleSerializer

    def perform_create(self, serializer):
        schedule = serializer.save(created_by=self.request.user)
        write_crontab(schedule)

    def perform_update(self, serializer):
        schedule = serializer.save()
        write_crontab(schedule)

    def perform_destroy(self, instance):
        crontab_path = settings.CRONTAB_PATH / f"ct_{instance.id}"
        if os.path.exists(crontab_path):
            os.remove(crontab_path)
        instance.delete()


class JobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Job.objects.select_related("schedule").all()
    serializer_class = JobSerializer


class CredentialViewSet(viewsets.ModelViewSet):
    queryset = Credential.objects.order_by("name")
    serializer_class = CredentialSerializer

    def perform_destroy(self, instance):
        instance.schedule_set.update(credential=None, active=False)
        instance.delete()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.order_by("username")
    serializer_class = UserSerializer


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie set."})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_view(request):
    user = authenticate(
        request,
        username=request.data.get("username", ""),
        password=request.data.get("password", ""),
    )
    if user is None:
        return Response({"detail": "Invalid username or password."}, status=400)
    login(request, user)
    return Response(UserSerializer(user).data)


@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response(status=204)


@api_view(["GET"])
def current_user(request):
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
def describe_cron(request):
    cron_rule = request.query_params.get("cron_rule", "")
    try:
        cron_rule = validate_cron_rule(cron_rule)
        return Response({"description": Schedule(cron_rule=cron_rule).cron_description})
    except serializers.ValidationError:
        return Response({"description": "Invalid cron expression"}, status=400)

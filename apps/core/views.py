import os

import cron_descriptor
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from apps.core.forms import ScheduleCreateForm, ScheduleUpdateForm
from apps.core.models import Credential, Job, Schedule

User = get_user_model()


class ScheduleListView(LoginRequiredMixin, ListView):
    template_name = "core/index.html"
    model = Schedule


class ScheduleCreateView(LoginRequiredMixin, CreateView):
    model = Schedule
    form_class = ScheduleCreateForm
    success_url = "/"

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.created_by = self.request.user
        self.object.save()

        schedule_id = str(self.object.id)
        cmd = settings.CRONJOB_CMD.format(schedule_id=schedule_id, cron_rule=self.object.cron_rule)
        crontab_path = settings.CRONTAB_PATH / f"ct_{schedule_id}"
        with open(crontab_path, "w", encoding="utf-8") as fh:
            fh.write(cmd + "\n")
        return response


class ScheduleUpdateView(LoginRequiredMixin, UpdateView):
    model = Schedule
    form_class = ScheduleUpdateForm
    success_url = "/"

    def form_valid(self, form):
        response = super().form_valid(form)
        schedule_id = str(self.object.id)
        cmd = settings.CRONJOB_CMD.format(schedule_id=schedule_id, cron_rule=self.object.cron_rule)
        crontab_path = settings.CRONTAB_PATH / f"ct_{schedule_id}"
        with open(crontab_path, "w", encoding="utf-8") as fh:
            fh.write(cmd + "\n")
        return response


class ScheduleDeleteView(LoginRequiredMixin, DeleteView):
    model = Schedule
    success_url = "/"

    def form_valid(self, form):
        file_path = settings.CRONTAB_PATH / f"ct_{self.object.id}"
        if os.path.exists(file_path):
            os.remove(file_path)
        return super().form_valid(form)


class JobListView(LoginRequiredMixin, ListView):
    model = Job
    success_url = "/"


class JobLogDetailView(LoginRequiredMixin, DetailView):
    model = Job
    template_name = "core/job_log.html"


class CredentialListView(LoginRequiredMixin, ListView):
    model = Credential


class CredentialCreateView(LoginRequiredMixin, CreateView):
    model = Credential
    fields = ["name", "username", "password", "category"]
    success_url = reverse_lazy("credential-list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        category = self.request.GET.get("category") or self.request.POST.get("category")
        form.fields["password"].widget = forms.PasswordInput()
        if category == "3":  # AWS
            form.fields["username"].required = True
            form.fields["password"].required = True

        return form


class CredentialUpdateView(LoginRequiredMixin, UpdateView):
    model = Credential
    fields = ["name", "username", "password", "category"]
    success_url = reverse_lazy("credential-list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        category = self.request.GET.get("category") or self.request.POST.get("category")
        form.fields["password"].widget = forms.PasswordInput()
        if category == "3":  # AWS
            form.fields["username"].required = True
            form.fields["password"].required = True

        return form


class CredentialDeleteView(LoginRequiredMixin, DeleteView):
    model = Credential
    success_url = reverse_lazy("credential-list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["agreement"] = forms.BooleanField(
            label="I understand that this action will remove the credential from these schedules and disable them.",
            required=True,
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["related_schedules"] = self.get_object().schedule_set.all()
        return context

    def post(self, request, *args, **kwargs):
        for schedule in self.get_object().schedule_set.all():
            schedule.credential = None
            schedule.active = False
            schedule.save()

        return self.delete(request, *args, **kwargs)


class DescribeCronView(LoginRequiredMixin, View):
    def get(self, request):
        cron_options = cron_descriptor.Options()
        cron_options.verbose = True
        cron_options.use_24hour_time_format = True

        cron_rule = request.GET.get("cron_rule")

        try:
            description = cron_descriptor.ExpressionDescriptor(cron_rule, cron_options).get_description()
        except (cron_descriptor.FormatException, cron_descriptor.Exception.MissingFieldException):
            return HttpResponse("Invalid cron expression")
        return HttpResponse(description)


class UserListView(LoginRequiredMixin, ListView):
    model = User


class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    fields = ["username", "email", "first_name", "last_name"]
    success_url = reverse_lazy("user-list")


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ["username", "email", "first_name", "last_name"]
    success_url = reverse_lazy("user-list")


class UserDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    success_url = reverse_lazy("user-list")

import os

import cron_descriptor
from django import forms
from django.conf import settings
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


class ScheduleListView(ListView):
    template_name = "core/index.html"
    model = Schedule


class ScheduleCreateView(CreateView):
    model = Schedule
    form_class = ScheduleCreateForm
    success_url = "/"

    def form_valid(self, form):
        response = super().form_valid(form)
        schedule_id = str(self.object.id)
        filename = f"ct_{schedule_id}"
        cmd = f"* * * * *   root	echo '{filename}'"
        crontab_path = settings.CRONTAB_PATH / filename
        with open(crontab_path, "w", encoding="utf-8") as fh:
            fh.write(cmd)
        return response


class ScheduleUpdateView(UpdateView):
    model = Schedule
    form_class = ScheduleUpdateForm
    success_url = "/"


class ScheduleDeleteView(DeleteView):
    model = Schedule
    success_url = "/"

    def form_valid(self, form):
        file_path = settings.CRONTAB_PATH / f"ct_{self.object.id}"
        if os.path.exists(file_path):
            os.remove(file_path)
        return super().form_valid(form)


class JobListView(ListView):
    model = Job
    success_url = "/"


class JobLogDetailView(DetailView):
    model = Job
    template_name = "core/job_log.html"


class CredentialListView(ListView):
    model = Credential


class CredentialCreateView(CreateView):
    model = Credential
    success_url = reverse_lazy("credential-list")
    fields = ["name", "username", "password", "category"]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        category = self.request.GET.get("category") or self.request.POST.get("category")

        if category == "3":  # AWS
            form.fields["username"].required = True
            form.fields["password"].required = True

        return form


class CredentialUpdateView(UpdateView):
    model = Credential
    fields = ["name", "username", "password", "category"]

    success_url = reverse_lazy("credential-list")


class CredentialDeleteView(DeleteView):
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


class DescribeCronView(View):
    def get(self, request):
        cron_options = cron_descriptor.Options()
        cron_options.verbose = True

        cron_rule = request.GET.get("cron_rule")

        print(f"{cron_rule=}")

        description = cron_descriptor.ExpressionDescriptor(
            cron_rule, cron_options
        ).get_description()
        return HttpResponse(description)

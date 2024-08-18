import os
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, DeleteView, DetailView, UpdateView

from apps.core.forms import ScheduleCreateForm, ScheduleUpdateForm
from apps.core.models import Schedule, Job, Credential


class ScheduleListView(ListView):
    template_name = "core/index.html"
    model = Schedule


class ScheduleCreateView(CreateView):
    model = Schedule
    form_class = ScheduleCreateForm
    success_url = "/"

    def form_valid(self, form):
        print("Create crontab entry")
        response = super().form_valid(form)
        schedule_id = str(self.object.id)
        filename = f"ct_{schedule_id}"
        cmd = f"* * * * *   root	echo '{filename}'"
        crontab_path = os.path.join(settings.BASE_DIR, "cron.d", filename)
        with open(crontab_path, "w") as fh:
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
        file_path = os.path.join(settings.BASE_DIR, "cron.d", f"ct_{self.object.id}")
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


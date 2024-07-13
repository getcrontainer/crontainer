import os
from django.conf import settings
from django.views.generic import CreateView, ListView, DeleteView
from apps.core.models import Schedule


class ScheduleListView(ListView):
    template_name = "core/index.html"
    model = Schedule


class ScheduleCreateView(CreateView):
    model = Schedule
    fields = [
        "name",
        "parameters",
        "cron_rule",
        "active",
        "singleton",
        "env_vars",
        "image",
        "credential",
        "cpu",
        "memory",
    ]
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


class ScheduleDeleteView(DeleteView):
    model = Schedule
    success_url = "/"

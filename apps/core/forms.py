import cron_descriptor
from django import forms
from django.core.exceptions import ValidationError

from apps.core.models import Schedule


class ScheduleCreateForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = [
            "name",
            "cmd",
            "cron_rule",
            "active",
            "singleton",
            "env_vars",
            "image",
            "credential",
            "cpu",
            "memory",
        ]

    def clean_cron_rule(self):
        data = self.cleaned_data["cron_rule"]
        if len(data.split(" ")) != 5:
            raise ValidationError("Cronjob expression is composed of 5 elements")

        from cron_descriptor import get_description, ExpressionDescriptor
        try:
            get_description(data)
        except cron_descriptor.Exception.FormatException:
            raise ValidationError("Not a valid cronjob expression")

        return data

import re

import cron_descriptor
from cron_descriptor import get_description
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy

from apps.core.models import Schedule

env_var_key_regex = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


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

        widgets = {
            "cron_rule": forms.TextInput(
                attrs={
                    "hx-get": reverse_lazy("describe_cron"),
                    "hx-trigger": "input change delay:500ms",
                    "hx-target": "#cron-description",
                }
            ),
        }

    def clean_cron_rule(self):
        data = self.cleaned_data["cron_rule"]
        if len(data.split(" ")) != 5:
            raise ValidationError("Cronjob expression is composed of 5 elements")
        try:
            get_description(data)
        except cron_descriptor.Exception.FormatException as err:
            raise ValidationError("Not a valid cronjob expression") from err

        return data

    def clean_env_vars(self):
        keys = self.data.getlist("env_vars_keys")
        values = self.data.getlist("env_vars_values")

        for key, value in zip(keys, values):
            if not value:
                raise ValidationError(f"Value for environment variable '{key}' is required")

            if not env_var_key_regex.match(key):
                raise ValidationError(f"Invalid environment variable key: '{key}'")

        return dict(zip(keys, values))


class ScheduleUpdateForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = [
            "name",
            "cmd",
            "cron_rule",
            "active",
            "singleton",
            "env_vars",
            "credential",
            "cpu",
            "memory",
        ]

        widgets = {
            "cron_rule": forms.TextInput(
                attrs={
                    "hx-get": reverse_lazy("describe_cron"),
                    "hx-trigger": "input change delay:500ms",
                    "hx-target": "#cron-description",
                }
            ),
        }

    def clean_cron_rule(self):
        data = self.cleaned_data["cron_rule"]
        if len(data.split(" ")) != 5:
            raise ValidationError("Cronjob expression is composed of 5 elements")
        try:
            get_description(data)
        except cron_descriptor.Exception.FormatException as err:
            raise ValidationError("Not a valid cronjob expression") from err

        return data

    def clean_env_vars(self):
        keys = self.data.getlist("env_vars_keys")
        values = self.data.getlist("env_vars_values")

        for key, value in zip(keys, values):
            if not value:
                raise ValidationError(f"Value for environment variable '{key}' is required")

            if not env_var_key_regex.match(key):
                raise ValidationError(f"Invalid environment variable key: '{key}'")

        return dict(zip(keys, values))

from cron_descriptor import ExpressionDescriptor, FormatException, Options
from django import template

from apps.core.models import Credential, Job, Schedule
from apps.node.models import Node

register = template.Library()

cron_options = Options()

cron_options.verbose = True
cron_options.use_24hour_time_format = True


@register.filter(name="describe_cron")
def describe_cron(value):
    try:
        return ExpressionDescriptor(value, cron_options).get_description()
    except FormatException:
        return "Invalid cron expression"


@register.simple_tag
def resource_count(resource):
    if resource == "schedule":
        return Schedule.objects.all().count()

    if resource == "job":
        return Job.objects.all().count()

    if resource == "credential":
        return Credential.objects.all().count()

    if resource == "node":
        return Node.objects.all().count()

    return 0

from cron_descriptor import ExpressionDescriptor, FormatException, Options
from django import template

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

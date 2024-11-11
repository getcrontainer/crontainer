from cron_descriptor import ExpressionDescriptor, Options
from django import template

register = template.Library()

cron_options = Options()

cron_options.verbose = True


@register.filter(name="describe_cron")
def describe_cron(value):
    return ExpressionDescriptor(value, cron_options).get_description()

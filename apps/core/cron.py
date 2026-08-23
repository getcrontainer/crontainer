"""Cron parsing shared by API validation and schedule descriptions."""

from cronsim import CronSim, CronSimError
from django.utils import timezone

CRON_FIELD_COUNT = 5


def parse_cron_rule(value: str) -> CronSim:
    """Parse a standard Debian-style five-field cron expression."""
    if len(value.split()) != CRON_FIELD_COUNT:
        raise CronSimError(f"Expected {CRON_FIELD_COUNT} fields")

    expression = CronSim(value, timezone.now())
    try:
        next(expression)
    except StopIteration as exc:
        raise CronSimError("Expression does not produce a future execution time") from exc
    return expression

"""Cron parsing shared by API validation and schedule descriptions."""

from cronsim import CronSim, CronSimError
from django.conf import settings
from django.utils import timezone

CRON_FIELD_COUNT = 5


def schedule_crontab_filename(schedule_id) -> str:
    """Return the cron definition filename for a schedule ID."""
    return f"ct_{schedule_id}"


def write_crontab(schedule) -> None:
    """Write a schedule's cron definition using the configured command template."""
    command = settings.CRONJOB_CMD.format(schedule_id=schedule.id, cron_rule=schedule.cron_rule)
    settings.CRONTAB_PATH.mkdir(parents=True, exist_ok=True)
    (settings.CRONTAB_PATH / schedule_crontab_filename(schedule.id)).write_text(f"{command}\n", encoding="utf-8")


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

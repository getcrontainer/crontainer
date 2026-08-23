"""Runtime health checks for the Crontainer service."""

import os
import shutil
from pathlib import Path

from django.conf import settings


def process_is_running(pid_file: Path, expected_command: str) -> bool:
    """Return whether a PID file points to a live process with the expected command."""
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        if pid <= 0:
            return False
        os.kill(pid, 0)
        command = (Path("/proc") / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8")
    except (OSError, UnicodeError, ValueError):
        return False
    return expected_command in command


def disk_health() -> dict:
    """Return health details for the filesystem containing persistent application data."""
    path = settings.HEALTH_DISK_PATH
    threshold = settings.HEALTH_DISK_MAX_USED_PERCENT
    try:
        usage = shutil.disk_usage(path)
        used_percent = round((usage.used / usage.total) * 100, 2) if usage.total else 100.0
        healthy = used_percent < threshold
        return {
            "status": "healthy" if healthy else "unhealthy",
            "healthy": healthy,
            "path": str(path),
            "used_percent": used_percent,
            "max_used_percent": threshold,
        }
    except OSError as exc:
        return {
            "status": "unhealthy",
            "healthy": False,
            "path": str(path),
            "used_percent": None,
            "max_used_percent": threshold,
            "error": str(exc),
        }


def get_system_health() -> dict:
    """Aggregate process and disk checks into the API response payload."""
    cron_running = process_is_running(settings.CRON_PID_FILE, "cron")
    updater_running = process_is_running(settings.JOB_UPDATER_PID_FILE, "manage.py update_history")
    checks = {
        "cron": {
            "status": "healthy" if cron_running else "unhealthy",
            "healthy": cron_running,
            "running": cron_running,
        },
        "job_updater": {
            "status": "healthy" if updater_running else "unhealthy",
            "healthy": updater_running,
            "running": updater_running,
        },
        "disk": disk_health(),
    }
    healthy = all(check["healthy"] for check in checks.values())
    return {"status": "healthy" if healthy else "unhealthy", "healthy": healthy, "checks": checks}

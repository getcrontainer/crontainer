import time

import docker
from django.core.management.base import BaseCommand

from apps.core.models import Job

MISSING_CONTAINER_STATUS_CODE = -400


class Command(BaseCommand):
    help = "Update job status"

    @staticmethod
    def _check_container(job: Job):
        container_name = str(job.id)
        client = docker.from_env()
        try:
            container = client.containers.get(container_name)
        except docker.errors.NotFound:
            container = None
        return container

    def _update_job(self, job: Job):
        container = self._check_container(job)
        if not container:
            message = f"Docker container {job.id} was not found while the job was unfinished."
            self.stdout.write(self.style.ERROR(f"{job.schedule.id} - {job.id} - {message}"))
            job.state = {"Status": "missing", "Error": message}
            job.status = "failure"
            job.status_code = MISSING_CONTAINER_STATUS_CODE
            job.log = message
            job.save(update_fields=["state", "status", "status_code", "log"])
            return

        job.state = container.attrs["State"]
        job.status = container.status
        job.save(update_fields=["state", "status"])

        if container.status == "exited":
            self.stdout.write(self.style.SUCCESS(f"{job.schedule.id} - {job.id} - finished job, removing container..."))
            job.log = container.logs().decode("utf-8")
            job.status_code = container.wait()["StatusCode"]
            job.save(update_fields=["log", "status_code"])
            container.remove()
        else:
            self.stdout.write(self.style.WARNING(f"{job.schedule.id} - {job.id} - still running..."))

    def handle(self, *args, **options):
        while True:
            self.stdout.write(self.style.SUCCESS("Checking for jobs to update..."))
            for job in Job.objects.filter(status_code__isnull=True, provisioning=False):
                self.stdout.write(self.style.WARNING(f"{job.schedule.id} - {job.id} - processing job"))
                self._update_job(job)
            time.sleep(60)

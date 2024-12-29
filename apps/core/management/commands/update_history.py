import docker
from django.core.management.base import BaseCommand

from apps.core.models import Job


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

    def handle(self, *args, **options):
        for job in Job.objects.filter(status_code__isnull=True, provisioning=False):
            self.stdout.write(self.style.WARNING(f"{job.schedule.id} - {job.id} - processing job"))
            container = self._check_container(job)
            if container:
                job.state = container.attrs["State"]
                job.status = container.status
                job.save()

                if container.status == "exited":
                    self.stdout.write(
                        self.style.SUCCESS(f"{job.schedule.id} - {job.id} - finished job, removing container...")
                    )
                    job.log = container.logs().decode("utf-8")
                    job.status_code = container.wait()["StatusCode"]
                    job.save()
                    container.remove()
                else:
                    self.stdout.write(self.style.WARNING(f"{job.schedule.id} - {job.id} - still running..."))
            else:
                self.stdout.write(self.style.ERROR(f"{job.schedule.id} - {job.id} - can't find container"))

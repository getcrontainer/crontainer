import time
import docker

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.core.models import Schedule, Job


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def handle(self, *args, **options):
        client = docker.from_env()
        for job in Job.objects.filter(status_code__isnull=True, provisioning=False):
            print(f"processing job {job.id} for schedule {job.schedule.name}")
            container_name = str(job.id)

            try:
                container = client.containers.get(container_name)
            except docker.errors.NotFound:
                print("Can´t find this container", container_name)
                container = None

            if container:
                job.state = container.attrs["State"]
                job.status = container.status
                job.save()

                if container.status == "exited":
                    print("Finished job, removing container")
                    job.log = container.logs().decode("utf-8")
                    job.status_code = container.wait()["StatusCode"]
                    job.save()
                    container.remove()

            self.stdout.write(
                self.style.SUCCESS('Successfully started Schedule job "%s"' % job.id)
            )

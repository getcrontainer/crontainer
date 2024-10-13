import sys
import time

import docker
from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Job, Schedule

client = docker.from_env()


class Command(BaseCommand):
    help = "Start a cronjob by schedule ID"

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout=None, stderr=None, no_color=False, force_color=False)
        self.schedule = None
        self.job = None
        self.local_image = None

    def add_arguments(self, parser):
        parser.add_argument("schedule_id", type=str)

    def handle(self, *args, **options):
        schedule_id = options["schedule_id"]
        try:
            self.schedule = Schedule.objects.get(pk=schedule_id)
        except Schedule.DoesNotExist:
            raise CommandError('Schedule "%s" does not exist' % schedule_id)

        self.job = Job.objects.create(schedule_id=schedule_id, provisioning=True)

        if self.schedule.image.lower().startswith(("http://", "https://")):
            self.build_image()
        else:
            self.pull_image()
        self.start_container()

        self.stdout.write(
            self.style.SUCCESS('Successfully started Schedule job "%s"' % schedule_id)
        )

    def build_image(self):
        try:
            x = client.images.build(
                path=self.schedule.image + "#main", tag="abacate:latest"
            )
            for i in x[1]:
                print(i)
            self.local_image = "abacate:latest"

        except Exception as e:
            self.job.exception_on_build = True
            self.job.log = e
            self.job.status = "failure"
            self.job.status_code = -100
            self.job.save()
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to [build image] for Schedule job {self.schedule.id}"
                )
            )
            sys.exit(0)

    def pull_image(self):
        start_time = time.time()
        print("Pulling image")
        credential = self.schedule.credential
        credential = credential.json() if credential else None
        try:
            client.images.pull(self.schedule.image, auth_config=credential)
            # client.api.pull(self.schedule.image, auth_config=credential)
        except Exception as e:
            self.job.exception_on_pull = True
            self.job.log = e
            self.job.status = "failure"
            self.job.status_code = -200
            self.job.save()
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to [pull image] for Schedule job {self.schedule.id}"
                )
            )
            sys.exit(0)

        print(time.time() - start_time)

    def start_container(self):
        image = self.local_image or self.schedule.image
        cmd = self.schedule.cmd or None
        try:
            client.containers.run(image, cmd, detach=True, name=self.job.id)
            self.job.provisioning = False
            self.job.save()
        except docker.errors.APIError as e:
            self.job.exception_on_run = True
            self.job.log = e
            self.job.status = "failure"
            self.job.status_code = -300
            self.job.save()
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to [run container] for Schedule job {self.schedule.id}"
                )
            )
            sys.exit(0)

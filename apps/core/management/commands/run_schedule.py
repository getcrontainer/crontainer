import sys
import time

import docker
from django.core.exceptions import ValidationError
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

        # Check if schedule exists
        #
        try:
            self.schedule = Schedule.objects.get(pk=schedule_id)
        except Schedule.DoesNotExist as exc:
            raise CommandError(f"Schedule {schedule_id} does not exist") from exc
        except ValidationError as exc:
            raise CommandError(f"Input {schedule_id} is not a valid schedule id format") from exc

        # Check if schedule is active
        #
        if not self.schedule.active:
            self.stdout.write(self.style.WARNING(f"Schedule {schedule_id} is not active, aborting..."))
            sys.exit(0)

        # Check if schedule is a singleton and no previous job is already running
        #
        if self.schedule.singleton:
            if Job.objects.filter(schedule_id=schedule_id).exclude(status="exited").exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Schedule {schedule_id} is a singleton and a Job is already running, aborting..."
                    )
                )
                sys.exit(0)

        # Job Provisioning
        #
        self.job = Job.objects.create(schedule_id=schedule_id, provisioning=True)

        if self.schedule.image.lower().startswith(("http://", "https://")):
            self.build_image()
        else:
            self.pull_image()
        self.start_container()

        self.stdout.write(self.style.SUCCESS(f"Successfully started job from Schedule {schedule_id}"))
        self.stdout.write(self.style.SUCCESS(f"Job ID: {self.job.id}"))

    def build_image(self):
        try:
            x = client.images.build(path=self.schedule.image + "#main", tag="abacate:latest")
            for i in x[1]:
                print(i)
            self.local_image = "abacate:latest"

        except Exception as e:
            self.job.exception_on_build = True
            self.job.log = e
            self.job.status = "failure"
            self.job.status_code = -100
            self.job.save()
            self.stdout.write(self.style.ERROR(f"Failed to [build image] for Schedule job {self.schedule.id}"))
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
            self.stdout.write(self.style.ERROR(f"Failed to [pull image] for Schedule job {self.schedule.id}"))
            sys.exit(0)

        print(time.time() - start_time)

    def start_container(self):
        image = self.local_image or self.schedule.image
        cmd = self.schedule.cmd or None
        # Docker API expects memory in bytes
        memory_limit = self.schedule.memory * int(1e6) if self.schedule.memory else None
        # Docker API expects CPU in nano_cpus (where 1 CPU = 1e9 nano_cpus)
        cpu_limit = self.schedule.cpu * int(1e9) if self.schedule.cpu else None

        try:
            client.containers.run(
                image,
                cmd,
                detach=True,
                name=self.job.id,
                environment=self.schedule.env_vars,
                mem_limit=memory_limit,
                nano_cpus=cpu_limit,
            )
            self.job.provisioning = False
            self.job.save()
        except docker.errors.APIError as e:
            self.job.exception_on_run = True
            self.job.log = e
            self.job.status = "failure"
            self.job.status_code = -300
            self.job.save()
            self.stdout.write(self.style.ERROR(f"Failed to [run container] for Schedule job {self.schedule.id}"))
            sys.exit(0)

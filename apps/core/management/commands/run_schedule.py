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

        self.stdout.write(self.style.SUCCESS(f"[{schedule_id}] successfully started job: {self.job.id}"))

    def build_image(self):
        start_time = time.time()
        self.stdout.write(self.style.WARNING(f"[{self.schedule.id}] building image {self.schedule.image}"))
        try:
            _image, build_log = client.images.build(
                path=self.schedule.image + "#main", tag=f"{self.schedule.id}:latest"
            )
            for step in build_log:
                assert step
            self.local_image = f"{self.schedule.id}:latest"

        except Exception as e:
            self.process_exception(e, "build")
            self.stdout.write(self.style.ERROR(f"[{self.schedule.id}] failed to build image"))
            sys.exit(0)

        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.WARNING(f"[{self.schedule.id}] build image time: {elapsed_time:.2f}s"))

    def pull_image(self):
        start_time = time.time()
        self.stdout.write(self.style.WARNING(f"[{self.schedule.id}] pulling image {self.schedule.image}"))
        credential = self.schedule.credential
        credential = credential.json() if credential else None
        try:
            response = client.api.pull(self.schedule.image, auth_config=credential, stream=True, decode=True)
            for step in response:
                assert step
        except Exception as e:
            self.process_exception(e, "pull")
            self.stdout.write(self.style.ERROR(f"[{self.schedule.id}] failed to pull image"))
            sys.exit(0)

        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.WARNING(f"[{self.schedule.id}] pull image time: {elapsed_time:.2f}s"))

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
            self.process_exception(e, "run")
            self.stdout.write(self.style.ERROR(f"Failed to [run container] for Schedule job {self.schedule.id}"))
            sys.exit(0)

    def process_exception(self, e: Exception, step: str) -> None:
        """
        Handles and processes exceptions occurring during specific steps of a job execution.
        Updates job attributes to reflect the encountered error, modifies the job status, and logs
        the exception.

        Parameters:
            e (Exception): The exception object that should be logged and processed.
            step (str): The job execution step where the exception occurred. Expected values are
                "run", "build", or "pull".
        """
        if step == "run":
            self.job.exception_on_run = True
            self.job.status_code = -300
        elif step == "build":
            self.job.exception_on_build = True
            self.job.status_code = -100
        elif step == "pull":
            self.job.exception_on_pull = True
            self.job.status_code = -200

        self.job.log = e
        self.job.status = "failure"
        self.job.save()

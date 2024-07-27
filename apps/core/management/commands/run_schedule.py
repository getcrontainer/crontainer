import time
import docker

from django.core.management.base import BaseCommand, CommandError
from apps.core.models import Schedule, Job

client = docker.from_env()


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout=None, stderr=None, no_color=False, force_color=False)
        self.schedule = None
        self.job = None
        self.local_image = None

    def add_arguments(self, parser):
        parser.add_argument("schedule_id", nargs="+", type=str)

    def handle(self, *args, **options):
        for schedule_id in options["schedule_id"]:
            try:
                self.schedule = Schedule.objects.get(pk=schedule_id)
            except Schedule.DoesNotExist:
                raise CommandError('Schedule "%s" does not exist' % schedule_id)

            self.job = Job.objects.create(schedule_id=schedule_id)

            if self.schedule.image.lower().startswith(("http://", "https://")):
                self.build_image()
            else:
                self.pull_image()
            self.start_container()

            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully started Schedule job "%s"' % schedule_id
                )
            )

    def build_image(self):
        x = client.images.build(
            path=self.schedule.image + "#main", tag="abacate:latest"
        )
        for i in x[1]:
            print(i)
        self.local_image = "abacate:latest"

    def pull_image(self):
        print("Pulling image")
        start_time = time.time()
        image = client.api.pull(self.schedule.image)
        print(image)
        print(time.time() - start_time)

    def start_container(self):
        image = self.local_image or self.schedule.image
        try:
            client.containers.run(image, "sleep 15", detach=True, name=self.job.id)
        except docker.errors.APIError as e:
            self.job.exception_on_run = True
            self.job.log = e
            self.job.save()

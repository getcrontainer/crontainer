import time

from django.core.management.base import BaseCommand, CommandError
from apps.core.models import Schedule


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        parser.add_argument("schedule_id", nargs="+", type=str)

    def handle(self, *args, **options):
        for schedule_id in options["schedule_id"]:
            try:
                schedule = Schedule.objects.get(pk=schedule_id)
            except Schedule.DoesNotExist:
                raise CommandError('Schedule "%s" does not exist' % schedule_id)

            import docker

            client = docker.from_env()
            print("Pulling image")
            image = client.images.pull(schedule.image)
            print(image)

            container = client.containers.run("ubuntu", "sleep 5", detach=True)

            for i in range(10):
                time.sleep(1)
                print(container.reload())
                print(container.status)

            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully started Schedule job "%s"' % schedule_id
                )
            )

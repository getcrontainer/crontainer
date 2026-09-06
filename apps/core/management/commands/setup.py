from django.core.management.base import BaseCommand

from apps.core.helper import create_superuser_on_startup
from apps.node.models import Node


class Command(BaseCommand):
    help = "..."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Setting up Crontainer"))
        self.stdout.write(self.style.SUCCESS("[1] Creating/Updating admin account"))
        create_superuser_on_startup()

        self.stdout.write(self.style.SUCCESS("[2] Adding default Docker Node (local)"))
        Node.objects.get_or_create(
            unix_socket="/var/run/docker.sock",
            defaults={"name": "local"},
        )

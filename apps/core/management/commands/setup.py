from django.core.management.base import BaseCommand

from apps.core.helper import create_superuser_on_startup


class Command(BaseCommand):
    help = "..."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Setting up Crontainer"))
        self.stdout.write(self.style.SUCCESS("[1] Creating/Updating admin account"))
        create_superuser_on_startup()

from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from apps.node.models import Node


class TestSetupCommand(TestCase):
    @patch("apps.core.management.commands.setup.create_superuser_on_startup")
    def test_setup_creates_the_default_node_once(self, create_superuser):
        call_command("setup")
        call_command("setup")

        self.assertEqual(create_superuser.call_count, 2)
        self.assertEqual(Node.objects.filter(unix_socket="/var/run/docker.sock").count(), 1)
        self.assertEqual(Node.objects.get(unix_socket="/var/run/docker.sock").name, "local")

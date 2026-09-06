from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.node.models import Node

User = get_user_model()


class TestNodeApi(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.client.force_login(self.user)

    def test_node_crud(self):
        response = self.client.post(
            "/api/nodes/",
            data={
                "name": "worker-1",
                "secret": "top-secret",
                "unix_socket": "/var/run/docker.sock",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        node_id = response.json()["id"]
        self.assertEqual(set(response.json()), {"id", "name", "unix_socket"})
        self.assertEqual(response.json()["unix_socket"], "/var/run/docker.sock")

        response = self.client.get("/api/nodes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()["results"][0]), {"id", "name", "unix_socket"})
        self.assertEqual(response.json()["results"][0]["name"], "worker-1")
        self.assertEqual(response.json()["results"][0]["unix_socket"], "/var/run/docker.sock")

        response = self.client.delete(f"/api/nodes/{node_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Node.objects.filter(id=node_id).exists())

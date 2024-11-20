from django.test import TestCase
from django.urls import reverse

from apps.core.tests.helpers import EasyResponse
from apps.node.models import Node


class TestNodeCreateView(TestCase):
    def test_get(self):
        response = self.client.get(reverse("node-create"))
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post(
            reverse("node-create"),
            {
                "name": "test",
                "host": "test",
                "port": 2375,
                "use_ssh": False,
                "secret": "test",
            },
            follow=True,
        )
        view = EasyResponse(response)

        self.assertTrue(len(view.object_list) == 1)

    def test_post_invalid(self):
        response = self.client.post(reverse("node-create"), {})
        view = EasyResponse(response)
        self.assertEqual(
            view.form.errors,
            {
                "name": ["This field is required."],
                "host": ["This field is required."],
                "port": ["This field is required."],
            },
        )
        self.assertEqual(response.status_code, 200)


class TestNodeUpdateView(TestCase):
    def setUp(self):
        self.node = Node.objects.create(
            name="test",
            host="test",
            port=2375,
            use_ssh=False,
        )

    def test_get(self):
        response = self.client.get(reverse("node-update", kwargs={"pk": self.node.id}))
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post(
            reverse("node-update", kwargs={"pk": self.node.id}),
            {
                "name": "test",
                "host": "test",
                "port": 2375,
                "use_ssh": False,
                "secret": "test",
            },
            follow=True,
        )
        view = EasyResponse(response)

        self.assertTrue(len(view.object_list) == 1)

    def test_post_invalid(self):
        response = self.client.post(reverse("node-update", kwargs={"pk": self.node.id}), {})
        view = EasyResponse(response)
        self.assertEqual(
            view.form.errors,
            {
                "name": ["This field is required."],
                "host": ["This field is required."],
                "port": ["This field is required."],
            },
        )
        self.assertEqual(response.status_code, 200)


class TestNodeDeleteView(TestCase):
    def setUp(self):
        self.node = Node.objects.create(
            name="test",
            host="test",
            port=2375,
            use_ssh=False,
        )

    def test_get(self):
        response = self.client.get(reverse("node-delete", kwargs={"pk": self.node.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "node/node_confirm_delete.html")

    def test_post(self):
        response = self.client.post(reverse("node-delete", kwargs={"pk": self.node.id}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "node/node_list.html")
        self.assertFalse(Node.objects.filter(id=self.node.id).exists())

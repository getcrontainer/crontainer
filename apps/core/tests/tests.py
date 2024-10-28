from django.test import TestCase
from django.urls import reverse

from apps.core.models import Credential
from apps.core.tests.helpers import EasyResponse


class TestCredentialCreateView(TestCase):
    def test_create_github_credentials_failure(self):
        response = self.client.post(reverse("credential-create"), data={"category": 2})
        view = EasyResponse(response)

        self.assertFalse(view.form.is_valid())

        self.assertTrue(view.form.errors.get("name"))
        self.assertFalse(view.form.errors.get("username"))
        self.assertTrue(view.form.errors.get("password"))
        self.assertFalse(view.form.errors.get("category"))

        self.assertEqual(view.form.data.get("name"), None)
        self.assertEqual(view.form.data.get("username"), None)
        self.assertEqual(view.form.data.get("password"), None)
        self.assertEqual(view.form.data.get("category"), "2")

    def test_create_github_credentials_success(self):
        response = self.client.post(
            reverse("credential-create"),
            data={"name": "github", "password": "pass", "category": 2},
            follow=True,
        )
        view = EasyResponse(response)

        credential_object: Credential = view.object_list.first()

        self.assertEqual(credential_object.name, "github")
        self.assertEqual(credential_object.password, "pass")
        self.assertEqual(credential_object.category, 2)
        self.assertEqual(credential_object.username, "")
        self.assertTrue(credential_object.id)

    def test_create_dockerhub_credentials_failure(self):
        response = self.client.post(reverse("credential-create"), data={"category": 1})
        view = EasyResponse(response)

        self.assertFalse(view.form.is_valid())

        self.assertTrue(view.form.errors.get("name"))
        self.assertFalse(view.form.errors.get("username"))
        self.assertTrue(view.form.errors.get("password"))
        self.assertFalse(view.form.errors.get("category"))

        self.assertEqual(view.form.data.get("name"), None)
        self.assertEqual(view.form.data.get("username"), None)
        self.assertEqual(view.form.data.get("password"), None)
        self.assertEqual(view.form.data.get("category"), "1")

    def test_create_dockerhub_credentials_success(self):
        response = self.client.post(
            reverse("credential-create"),
            data={
                "name": "dockerhub",
                "username": "user",
                "password": "pass",
                "category": 1,
            },
            follow=True,
        )
        view = EasyResponse(response)

        credential_object: Credential = view.object_list.first()

        self.assertEqual(credential_object.name, "dockerhub")
        self.assertEqual(credential_object.password, "pass")
        self.assertEqual(credential_object.category, 1)
        self.assertEqual(credential_object.username, "user")
        self.assertTrue(credential_object.id)

    def test_create_gitlab_credentials_failure(self):
        response = self.client.post(reverse("credential-create"), data={"category": 4})
        view = EasyResponse(response)

        self.assertFalse(view.form.is_valid())

        self.assertTrue(view.form.errors.get("name"))
        self.assertFalse(view.form.errors.get("username"))
        self.assertTrue(view.form.errors.get("password"))
        self.assertFalse(view.form.errors.get("category"))

        self.assertEqual(view.form.data.get("name"), None)
        self.assertEqual(view.form.data.get("username"), None)
        self.assertEqual(view.form.data.get("password"), None)
        self.assertEqual(view.form.data.get("category"), "4")

    def test_create_gitlab_credentials_success(self):
        response = self.client.post(
            reverse("credential-create"),
            data={
                "name": "gitlab",
                "password": "pass",
                "category": 4,
            },
            follow=True,
        )
        view = EasyResponse(response)

        credential_object: Credential = view.object_list.first()

        self.assertEqual(credential_object.name, "gitlab")
        self.assertEqual(credential_object.password, "pass")
        self.assertEqual(credential_object.category, 4)
        self.assertEqual(credential_object.username, "")
        self.assertTrue(credential_object.id)

    def test_create_generic_git_credentials_failure(self):
        response = self.client.post(reverse("credential-create"), data={"category": 98})
        view = EasyResponse(response)

        self.assertFalse(view.form.is_valid())

        self.assertTrue(view.form.errors.get("name"))
        self.assertFalse(view.form.errors.get("username"))
        self.assertTrue(view.form.errors.get("password"))
        self.assertFalse(view.form.errors.get("category"))

        self.assertEqual(view.form.data.get("name"), None)
        self.assertEqual(view.form.data.get("username"), None)
        self.assertEqual(view.form.data.get("password"), None)
        self.assertEqual(view.form.data.get("category"), "98")

    def test_create_generic_git_credentials_success(self):
        response = self.client.post(
            reverse("credential-create"),
            data={
                "name": "git",
                "password": "pass",
                "category": 98,
            },
            follow=True,
        )
        view = EasyResponse(response)

        credential_object: Credential = view.object_list.first()

        self.assertEqual(credential_object.name, "git")
        self.assertEqual(credential_object.password, "pass")
        self.assertEqual(credential_object.category, 98)
        self.assertEqual(credential_object.username, "")
        self.assertTrue(credential_object.id)

    def test_create_aws_credentials_failure(self):
        response = self.client.post(reverse("credential-create"), data={"category": 3})
        view = EasyResponse(response)

        self.assertFalse(view.form.is_valid())

        self.assertTrue(view.form.errors.get("name"))
        self.assertTrue(view.form.errors.get("username"))
        self.assertTrue(view.form.errors.get("password"))
        self.assertFalse(view.form.errors.get("category"))

        self.assertEqual(view.form.data.get("name"), None)
        self.assertEqual(view.form.data.get("username"), None)
        self.assertEqual(view.form.data.get("password"), None)
        self.assertEqual(view.form.data.get("category"), "3")

    def test_create_aws_credentials_success(self):
        response = self.client.post(
            reverse("credential-create"),
            data={
                "name": "aws",
                "username": "aws_id",
                "password": "aws_secret",
                "category": 3,
            },
            follow=True,
        )
        view = EasyResponse(response)

        credential_object: Credential = view.object_list.first()

        self.assertEqual(credential_object.name, "aws")
        self.assertEqual(credential_object.username, "aws_id")
        self.assertEqual(credential_object.password, "aws_secret")
        self.assertEqual(credential_object.category, 3)
        self.assertTrue(credential_object.id)


class TestCredentialDeleteView(TestCase):
    def test_delete_credential(self):
        credential = Credential.objects.create(
            name="test",
            username="test",
            password="test",
            category=1,
        )

        response = self.client.post(
            reverse("credential-delete", kwargs={"pk": credential.id}),
            follow=True,
        )
        view = EasyResponse(response)

        self.assertFalse(Credential.objects.filter(id=credential.id).exists())
        self.assertEqual(view.object_list.count(), 0)

from django.test import TestCase
from django.urls import reverse

from apps.core.models import CategoryChoices, Credential
from apps.core.tests.helpers import EasyResponse


class TestCredentialCreateView(TestCase):
    def test_create_github_credentials_failure(self):
        response = self.client.post(
            reverse("credential-create"), data={"category": CategoryChoices.GITHUB_PAT}
        )
        view = EasyResponse(response)

        self.assertFalse(view.form.is_valid())

        self.assertTrue(view.form.errors.get("name"))
        self.assertFalse(view.form.errors.get("username"))
        self.assertTrue(view.form.errors.get("password"))
        self.assertFalse(view.form.errors.get("category"))

        self.assertEqual(view.form.data.get("name"), None)
        self.assertEqual(view.form.data.get("username"), None)
        self.assertEqual(view.form.data.get("password"), None)
        self.assertEqual(
            view.form.data.get("category"), str(CategoryChoices.GITHUB_PAT)
        )

    def test_create_github_credentials_success(self):
        response = self.client.post(
            reverse("credential-create"),
            data={
                "name": "github",
                "password": "pass",
                "category": CategoryChoices.GITHUB_PAT,
            },
            follow=True,
        )
        view = EasyResponse(response)

        credential_object: Credential = view.object_list.first()

        self.assertEqual(credential_object.name, "github")
        self.assertEqual(credential_object.password, "pass")
        self.assertEqual(credential_object.category, CategoryChoices.GITHUB_PAT)
        self.assertEqual(credential_object.username, "")
        self.assertTrue(credential_object.id)

    def test_create_dockerhub_credentials_failure(self):
        response = self.client.post(
            reverse("credential-create"), data={"category": CategoryChoices.DOCKERHUB}
        )
        view = EasyResponse(response)

        self.assertFalse(view.form.is_valid())

        self.assertTrue(view.form.errors.get("name"))
        self.assertFalse(view.form.errors.get("username"))
        self.assertTrue(view.form.errors.get("password"))
        self.assertFalse(view.form.errors.get("category"))

        self.assertEqual(view.form.data.get("name"), None)
        self.assertEqual(view.form.data.get("username"), None)
        self.assertEqual(view.form.data.get("password"), None)
        self.assertEqual(view.form.data.get("category"), str(CategoryChoices.DOCKERHUB))

    def test_create_dockerhub_credentials_success(self):
        response = self.client.post(
            reverse("credential-create"),
            data={
                "name": "dockerhub",
                "username": "user",
                "password": "pass",
                "category": CategoryChoices.DOCKERHUB,
            },
            follow=True,
        )
        view = EasyResponse(response)

        credential_object: Credential = view.object_list.first()

        self.assertEqual(credential_object.name, "dockerhub")
        self.assertEqual(credential_object.password, "pass")
        self.assertEqual(credential_object.category, CategoryChoices.DOCKERHUB)
        self.assertEqual(credential_object.username, "user")
        self.assertTrue(credential_object.id)

    def test_create_gitlab_credentials_failure(self):
        response = self.client.post(
            reverse("credential-create"), data={"category": CategoryChoices.GITLAB_PAT}
        )
        view = EasyResponse(response)

        self.assertFalse(view.form.is_valid())

        self.assertTrue(view.form.errors.get("name"))
        self.assertFalse(view.form.errors.get("username"))
        self.assertTrue(view.form.errors.get("password"))
        self.assertFalse(view.form.errors.get("category"))

        self.assertEqual(view.form.data.get("name"), None)
        self.assertEqual(view.form.data.get("username"), None)
        self.assertEqual(view.form.data.get("password"), None)
        self.assertEqual(
            view.form.data.get("category"), str(CategoryChoices.GITLAB_PAT)
        )

    def test_create_gitlab_credentials_success(self):
        response = self.client.post(
            reverse("credential-create"),
            data={
                "name": "gitlab",
                "password": "pass",
                "category": CategoryChoices.GITLAB_PAT,
            },
            follow=True,
        )
        view = EasyResponse(response)

        credential_object: Credential = view.object_list.first()

        self.assertEqual(credential_object.name, "gitlab")
        self.assertEqual(credential_object.password, "pass")
        self.assertEqual(credential_object.category, CategoryChoices.GITLAB_PAT)
        self.assertEqual(credential_object.username, "")
        self.assertTrue(credential_object.id)

    def test_create_generic_git_credentials_failure(self):
        response = self.client.post(
            reverse("credential-create"), data={"category": CategoryChoices.GENERIC_GIT}
        )
        view = EasyResponse(response)

        self.assertFalse(view.form.is_valid())

        self.assertTrue(view.form.errors.get("name"))
        self.assertFalse(view.form.errors.get("username"))
        self.assertTrue(view.form.errors.get("password"))
        self.assertFalse(view.form.errors.get("category"))

        self.assertEqual(view.form.data.get("name"), None)
        self.assertEqual(view.form.data.get("username"), None)
        self.assertEqual(view.form.data.get("password"), None)
        self.assertEqual(
            view.form.data.get("category"), str(CategoryChoices.GENERIC_GIT)
        )

    def test_create_generic_git_credentials_success(self):
        response = self.client.post(
            reverse("credential-create"),
            data={
                "name": "git",
                "password": "pass",
                "category": CategoryChoices.GENERIC_GIT,
            },
            follow=True,
        )
        view = EasyResponse(response)

        credential_object: Credential = view.object_list.first()

        self.assertEqual(credential_object.name, "git")
        self.assertEqual(credential_object.password, "pass")
        self.assertEqual(credential_object.category, CategoryChoices.GENERIC_GIT)
        self.assertEqual(credential_object.username, "")
        self.assertTrue(credential_object.id)

    def test_create_aws_credentials_failure(self):
        response = self.client.post(
            reverse("credential-create"), data={"category": CategoryChoices.AWS_ECR}
        )
        view = EasyResponse(response)

        self.assertFalse(view.form.is_valid())

        self.assertTrue(view.form.errors.get("name"))
        self.assertTrue(view.form.errors.get("username"))
        self.assertTrue(view.form.errors.get("password"))
        self.assertFalse(view.form.errors.get("category"))

        self.assertEqual(view.form.data.get("name"), None)
        self.assertEqual(view.form.data.get("username"), None)
        self.assertEqual(view.form.data.get("password"), None)
        self.assertEqual(view.form.data.get("category"), str(CategoryChoices.AWS_ECR))

    def test_create_aws_credentials_success(self):
        response = self.client.post(
            reverse("credential-create"),
            data={
                "name": "aws",
                "username": "aws_id",
                "password": "aws_secret",
                "category": CategoryChoices.AWS_ECR,
            },
            follow=True,
        )
        view = EasyResponse(response)

        credential_object: Credential = view.object_list.first()

        self.assertEqual(credential_object.name, "aws")
        self.assertEqual(credential_object.username, "aws_id")
        self.assertEqual(credential_object.password, "aws_secret")
        self.assertEqual(credential_object.category, CategoryChoices.AWS_ECR)
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


class TestCredentialListView(TestCase):
    def test_list_credentials(self):
        Credential.objects.create(
            name="test",
            username="test",
            password="test",
            category=1,
        )

        response = self.client.get(reverse("credential-list"))
        view = EasyResponse(response)

        self.assertEqual(view.object_list.count(), 1)
        self.assertEqual(view.object_list.first().name, "test")
        self.assertEqual(view.object_list.first().username, "test")
        self.assertEqual(view.object_list.first().password, "test")
        self.assertEqual(view.object_list.first().category, 1)

    def test_list_credentials_empty(self):
        response = self.client.get(reverse("credential-list"))
        view = EasyResponse(response)

        self.assertEqual(view.object_list.count(), 0)

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.forms import Form

User = get_user_model()


class EasyResponse:
    def __init__(self, response):
        self.response = response

    @property
    def object_list(self) -> QuerySet:
        return self.response.context["object_list"]

    @property
    def form(self) -> Form:
        return self.response.context["form"]


def add_default_data():
    # Create a test user
    test_user, created = User.objects.get_or_create(username="testuser")
    if created:
        test_user.set_password("testpassword")
        test_user.email = "testuser@example.com"
        test_user.save()
    return test_user

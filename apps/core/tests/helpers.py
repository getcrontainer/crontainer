from django.db.models import QuerySet
from django.forms import Form


class EasyResponse:
    def __init__(self, response):
        self.response = response

    @property
    def object_list(self) -> QuerySet:
        return self.response.context["object_list"]

    @property
    def form(self) -> Form:
        return self.response.context["form"]


def add_default_data(): ...

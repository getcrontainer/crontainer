from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.node.models import Node


class NodeListView(ListView):
    model = Node


class NodeCreateView(CreateView):
    model = Node
    success_url = reverse_lazy("node-list")
    fields = ["name", "host", "port", "use_ssh", "secret"]


class NodeUpdateView(UpdateView):
    model = Node
    success_url = reverse_lazy("node-list")
    fields = ["name", "host", "port", "use_ssh", "secret"]


class NodeDeleteView(DeleteView):
    model = Node
    success_url = reverse_lazy("node-list")

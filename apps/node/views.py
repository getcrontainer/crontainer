from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.node.models import Node


class NodeListView(LoginRequiredMixin, ListView):
    model = Node


class NodeCreateView(LoginRequiredMixin, CreateView):
    model = Node
    success_url = reverse_lazy("node-list")
    fields = ["name", "host", "port", "use_ssh", "secret"]


class NodeUpdateView(LoginRequiredMixin, UpdateView):
    model = Node
    success_url = reverse_lazy("node-list")
    fields = ["name", "host", "port", "use_ssh", "secret"]


class NodeDeleteView(LoginRequiredMixin, DeleteView):
    model = Node
    success_url = reverse_lazy("node-list")

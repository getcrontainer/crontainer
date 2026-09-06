"""JSON API for Docker node configuration."""

from rest_framework import viewsets

from apps.node.models import Node
from apps.node.serializers import NodeSerializer


class NodeViewSet(viewsets.ModelViewSet):
    queryset = Node.objects.order_by("name")
    serializer_class = NodeSerializer

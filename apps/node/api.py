"""JSON API for Docker node configuration."""

from rest_framework import serializers, viewsets

from apps.node.models import Node


class NodeSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Node
        fields = ["id", "name", "secret", "unix_socket"]
        read_only_fields = ["id"]


class NodeViewSet(viewsets.ModelViewSet):
    queryset = Node.objects.order_by("name")
    serializer_class = NodeSerializer

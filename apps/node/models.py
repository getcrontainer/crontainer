import uuid

from django.db import models


class Node(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, unique=True)
    name = models.CharField(max_length=500)
    host = models.CharField(max_length=250, blank=True)
    port = models.IntegerField(default=2375, null=True)
    use_ssh = models.BooleanField(default=False)
    secret = models.CharField(max_length=500, blank=True)
    unix_socket = models.CharField(max_length=500, unique=True)

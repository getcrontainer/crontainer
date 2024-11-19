from django.urls import path

from apps.node.views import NodeCreateView, NodeDeleteView, NodeListView, NodeUpdateView

urlpatterns = [
    path("", NodeListView.as_view(), name="node-list"),
    path("create/", NodeCreateView.as_view(), name="node-create"),
    path("update/<uuid:pk>/", NodeUpdateView.as_view(), name="node-update"),
    path("delete/<uuid:pk>/", NodeDeleteView.as_view(), name="node-delete"),
]

from django.urls import path
from .views import ExternalURLView, MessageDetailView, MessageListView
urlpatterns = [path("", MessageListView.as_view()), path("<int:pk>/", MessageDetailView.as_view()), path("<int:pk>/external-url/", ExternalURLView.as_view())]

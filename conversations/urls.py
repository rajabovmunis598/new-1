from django.urls import path

from .views import (
    ConversationNoteDestroyView,
    ConversationNoteListCreateView,
    ConversationViewSet,
)


view = ConversationViewSet.as_view

urlpatterns = [
    path("", view({"get": "list"}), name="conversation-list"),
    path(
        "<int:pk>/",
        view({"get": "retrieve", "patch": "partial_update"}),
        name="conversation-detail",
    ),
    path("<int:pk>/close/", view({"post": "close"}), name="conversation-close"),
    path(
        "<int:pk>/archive/",
        view({"post": "archive"}),
        name="conversation-archive",
    ),
    path("<int:pk>/read/", view({"post": "read"}), name="conversation-read"),
    path("<int:pk>/pin/", view({"post": "pin"}), name="conversation-pin"),
    path(
        "<int:pk>/unpin/",
        view({"post": "unpin"}),
        name="conversation-unpin",
    ),
    path(
        "<int:pk>/snooze/",
        view({"post": "snooze"}),
        name="conversation-snooze",
    ),
    path(
        "<int:pk>/unsnooze/",
        view({"post": "unsnooze"}),
        name="conversation-unsnooze",
    ),
    path(
        "<int:conversation_pk>/notes/",
        ConversationNoteListCreateView.as_view(),
        name="conversation-note-list",
    ),
    path(
        "<int:conversation_pk>/notes/<int:note_id>/",
        ConversationNoteDestroyView.as_view(),
        name="conversation-note-detail",
    ),
]

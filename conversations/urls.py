from django.urls import path
from .views import ConversationViewSet
view = ConversationViewSet.as_view
urlpatterns = [path("", view({"get":"list"})), path("<int:pk>/", view({"get":"retrieve", "patch":"partial_update"})), path("<int:pk>/close/", view({"post":"close"})), path("<int:pk>/archive/", view({"post":"archive"}))]

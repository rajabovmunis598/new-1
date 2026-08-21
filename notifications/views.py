from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from .models import Notification
from .serializers import NotificationSerializer
class NotificationViewSet(ReadOnlyModelViewSet):
    queryset=Notification.objects.none()
    serializer_class=NotificationSerializer; filterset_fields=("type", "is_read")
    def get_queryset(self): return Notification.objects.filter(user=self.request.user)
    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        obj=self.get_object(); obj.is_read=True; obj.save(update_fields=["is_read"]); return Response(self.get_serializer(obj).data)
    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        count=self.get_queryset().filter(is_read=False).update(is_read=True); return Response({"updated":count})

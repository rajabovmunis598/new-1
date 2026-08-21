from django.db.models import Count, Q
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from .models import Conversation
from .serializers import ConversationSerializer

class ConversationViewSet(ModelViewSet):
    queryset = Conversation.objects.none()
    serializer_class = ConversationSerializer
    http_method_names = ("get", "patch", "post", "head", "options")
    filterset_fields = ("status", "contact", "integration")
    ordering_fields = ("created_at", "last_message_at")
    def get_queryset(self):
        qs = Conversation.objects.filter(integration__user=self.request.user).select_related("integration", "contact").annotate(unread_count=Count("messages", filter=Q(messages__is_read=False, messages__sender_type="customer")))
        platform = self.request.query_params.get("platform")
        if platform: qs = qs.filter(integration__platform=platform)
        if self.request.query_params.get("date_from"): qs = qs.filter(created_at__gte=self.request.query_params["date_from"])
        if self.request.query_params.get("date_to"): qs = qs.filter(created_at__lte=self.request.query_params["date_to"])
        return qs
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None): return self._status("closed")
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None): return self._status("archived")
    def _status(self, value):
        obj = self.get_object(); obj.status = value; obj.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(obj).data)

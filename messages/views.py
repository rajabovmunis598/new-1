from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from conversations.models import Conversation
from integrations.services import get_adapter
from .models import Message
from .serializers import MessageSerializer, OutgoingMessageSerializer

class MessageListView(generics.ListAPIView):
    queryset = Message.objects.none()
    serializer_class = MessageSerializer
    filterset_fields = ("sender_type", "message_type", "conversation", "is_read")
    search_fields = ("text", "conversation__contact__name", "conversation__contact__username", "conversation__contact__phone")
    ordering_fields = ("created_at", "external_created_at")
    def get_queryset(self):
        qs = Message.objects.filter(conversation__integration__user=self.request.user).select_related("conversation__integration", "conversation__contact")
        p = self.request.query_params
        if p.get("platform"): qs = qs.filter(conversation__integration__platform=p["platform"])
        if p.get("date_from"): qs = qs.filter(created_at__gte=p["date_from"])
        if p.get("date_to"): qs = qs.filter(created_at__lte=p["date_to"])
        return qs

class MessageDetailView(generics.RetrieveAPIView):
    queryset = Message.objects.none()
    serializer_class = MessageSerializer
    def get_queryset(self): return Message.objects.filter(conversation__integration__user=self.request.user).select_related("conversation__integration")

class SendMessageView(APIView):
    serializer_class = OutgoingMessageSerializer
    def post(self, request, pk):
        conversation = generics.get_object_or_404(Conversation, pk=pk, integration__user=request.user)
        serializer = OutgoingMessageSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        message = get_adapter(conversation.integration).send_message(conversation, serializer.validated_data["text"])
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

class ExternalURLView(APIView):
    def get(self, request, pk):
        message = generics.get_object_or_404(Message.objects.select_related("conversation__integration"), pk=pk, conversation__integration__user=request.user)
        return Response({"url": get_adapter(message.conversation.integration).get_external_url(message)})

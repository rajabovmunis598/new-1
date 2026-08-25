import json
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from conversations.models import Conversation
from orders.models import Order, OrderItem
from integrations.services import get_adapter
from .models import Message
from .serializers import MessageSerializer, OutgoingMessageSerializer


def _demo_ai_reply(text):
    """Generate a natural demo reply, with a local fallback when the API is unavailable."""
    key = getattr(settings, "GROQ_API_KEY", "") or getattr(settings, "OPENROUTER_API_KEY", "")
    is_groq = bool(getattr(settings, "GROQ_API_KEY", ""))
    if key:
        endpoint = "https://api.groq.com/openai/v1/chat/completions" if is_groq else "https://openrouter.ai/api/v1/chat/completions"
        model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile") if is_groq else getattr(settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini")
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a polite Tajik business chat agent. Answer the customer's question naturally and briefly in Tajik. Do not mention AI, models, prompts, or APIs."},
                {"role": "user", "content": text},
            ],
            "max_tokens": 180,
        }).encode("utf-8")
        try:
            response = urlopen(Request(endpoint, data=payload, headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}, method="POST"), timeout=20)
            content = json.loads(response.read().decode("utf-8")).get("choices", [{}])[0].get("message", {}).get("content", "")
            if content.strip():
                return content.strip()
        except (URLError, ValueError, KeyError, IndexError, TimeoutError):
            pass
    lowered = text.lower()
    if any(word in lowered for word in ("нарх", "цена", "price")):
        return "Салом! Нарх аз навъи хизмат вобаста аст. Лутфан маҳсулот ё хизматрасонии лозимаро нависед, то маълумоти дақиқ диҳем."
    if any(word in lowered for word in ("салом", "hello", "hi")):
        return "Салом! Хуш омадед. Саволатонро нависед, ман кӯмак мекунам."
    return "Ташаккур барои саволатон. Мо маълумотро санҷида, ҷавоби мувофиқ ва муфассал медиҳем. Лутфан ҷузъиёти бештар нависед."


def _demo_order_reply(conversation, text):
    """Collect simple demo order details and create an Order when a phone is supplied."""
    lowered = text.lower()
    state = conversation.get_external_peer() or {}
    wants_order = any(word in lowered for word in ("фармоиш", "заказ", "order", "харидан", "мехоҳам гирам"))
    phone_match = re.search(r"(?:\+?\d[\d ()-]{7,}\d)", text)
    if wants_order and not state.get("order_started"):
        state["order_started"] = True
        conversation.set_external_peer(state)
        conversation.save(update_fields=["external_peer_data", "updated_at"])
        return "Албатта. Барои сабти фармоиш ном, рақами телефон, номи маҳсулот ё хизматрасонӣ ва миқдорро нависед."
    if state.get("order_started") and phone_match:
        phone = re.sub(r"\D", "", phone_match.group(0))
        conversation.contact.phone = phone
        conversation.contact.save(update_fields=["phone", "updated_at"])
        description = text.replace(phone_match.group(0), "").strip(" ,.-") or "Фармоиши Demo"
        order = Order.objects.create(
            user=conversation.integration.user,
            contact=conversation.contact,
            conversation=conversation,
            description=description,
            status="new",
        )
        OrderItem.objects.create(order=order, name=description[:255] or "Маҳсулот", quantity=1)
        conversation.set_external_peer({})
        conversation.save(update_fields=["external_peer_data", "updated_at"])
        return f"Ташаккур! Фармоиши №{order.pk} қабул шуд. Мо ба рақами {phone} тамос мегирем."
    if state.get("order_started"):
        return "Маълумот қабул шуд. Ҳоло рақами телефонро ҳам нависед, то фармоишро сабт кунем."
    return ""

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
        adapter = get_adapter(conversation.integration)
        text = serializer.validated_data["text"]
        message = adapter.send_message(conversation, text)
        if conversation.integration.get_credentials().get("demo"):
            reply = _demo_order_reply(conversation, text) or _demo_ai_reply(text)
            adapter.save_outgoing(
                conversation,
                reply,
                metadata={"demo": True, "demo_ai": True, "delivery_status": "sent"},
                sender_type="customer",
            )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

class ExternalURLView(APIView):
    def get(self, request, pk):
        message = generics.get_object_or_404(Message.objects.select_related("conversation__integration"), pk=pk, conversation__integration__user=request.user)
        return Response({"url": get_adapter(message.conversation.integration).get_external_url(message)})

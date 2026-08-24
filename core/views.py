import json
from urllib.request import Request, urlopen

from django.conf import settings
from django.db.models import Count, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from contacts.models import Contact
from conversations.models import Conversation
from messages.models import Message
from orders.models import Order
from .openapi import (
    AISuggestionsRequestSerializer,
    AISuggestionsResponseSerializer,
    GlobalSearchResponseSerializer,
)


class DashboardStatisticsView(APIView):
    def get(self, request):
        messages = Message.objects.filter(
            conversation__integration__user=request.user
        )
        conversations = Conversation.objects.filter(
            integration__user=request.user
        )
        orders = Order.objects.filter(user=request.user)
        message_counts = messages.aggregate(
            total=Count("id"),
            unread=Count(
                "id",
                filter=Q(is_read=False, sender_type="customer"),
            ),
            telegram=Count(
                "id",
                filter=Q(conversation__integration__platform="telegram"),
            ),
            whatsapp=Count(
                "id",
                filter=Q(conversation__integration__platform="whatsapp"),
            ),
            instagram=Count(
                "id",
                filter=Q(conversation__integration__platform="instagram"),
            ),
        )
        conversation_counts = conversations.aggregate(
            total=Count("id"),
            opened=Count("id", filter=Q(status="open")),
        )
        order_counts = orders.aggregate(
            total=Count("id"),
            new=Count("id", filter=Q(status="new")),
            completed=Count("id", filter=Q(status="completed")),
        )
        return Response(
            {
                "total_messages": message_counts["total"],
                "unread_messages": message_counts["unread"],
                "telegram_messages": message_counts["telegram"],
                "whatsapp_messages": message_counts["whatsapp"],
                "instagram_messages": message_counts["instagram"],
                "total_conversations": conversation_counts["total"],
                "open_conversations": conversation_counts["opened"],
                "total_orders": order_counts["total"],
                "new_orders": order_counts["new"],
                "completed_orders": order_counts["completed"],
            }
        )


class GlobalSearchView(APIView):
    """Fast owner-scoped search for the command palette and power users."""

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "q",
                str,
                OpenApiParameter.QUERY,
                required=True,
                description="Search text (up to 100 characters).",
            )
        ],
        responses={200: GlobalSearchResponseSerializer},
        tags=["search"],
    )
    def get(self, request):
        query = str(request.query_params.get("q") or "").strip()[:100]
        if not query:
            return Response({"query": "", "results": []})

        contact_filter = (
            Q(name__icontains=query)
            | Q(username__icontains=query)
            | Q(phone__icontains=query)
            | Q(external_id__icontains=query)
        )
        results = []

        contacts = (
            Contact.objects.filter(integration__user=request.user)
            .filter(contact_filter)
            .select_related("integration")
            .order_by("-updated_at")[:5]
        )
        for contact in contacts:
            title = (
                contact.name
                or (f"@{contact.username}" if contact.username else "")
                or contact.phone
                or f"Муштарӣ #{contact.pk}"
            )
            subtitle = contact.phone or (
                f"@{contact.username}" if contact.username else contact.external_id
            )
            results.append(
                {
                    "type": "contact",
                    "id": contact.pk,
                    "title": title,
                    "subtitle": subtitle,
                    "url": f"/contacts?contact={contact.pk}",
                    "platform": contact.integration.platform,
                }
            )

        conversations = (
            Conversation.objects.filter(integration__user=request.user)
            .filter(
                Q(title__icontains=query)
                | Q(contact__name__icontains=query)
                | Q(contact__username__icontains=query)
                | Q(contact__phone__icontains=query)
            )
            .select_related("integration", "contact")
            .order_by("-last_message_at", "-pk")[:5]
        )
        for conversation in conversations:
            contact = conversation.contact
            title = (
                contact.name
                or (f"@{contact.username}" if contact.username else "")
                or conversation.title
                or f"Суҳбат #{conversation.pk}"
            )
            results.append(
                {
                    "type": "conversation",
                    "id": conversation.pk,
                    "title": title,
                    "subtitle": conversation.title or contact.phone or "Суҳбат",
                    "url": f"/messages?conversation={conversation.pk}",
                    "platform": conversation.integration.platform,
                    "status": conversation.status,
                }
            )

        orders = (
            Order.objects.filter(user=request.user)
            .filter(
                Q(external_id__icontains=query)
                | Q(description__icontains=query)
                | Q(contact__name__icontains=query)
                | Q(contact__username__icontains=query)
                | Q(contact__phone__icontains=query)
            )
            .select_related("contact", "conversation__integration")
            .order_by("-updated_at")[:5]
        )
        for order in orders:
            results.append(
                {
                    "type": "order",
                    "id": order.pk,
                    "title": f"Фармоиш #{order.pk}",
                    "subtitle": order.description or order.external_id or "Фармоиш",
                    "url": f"/orders?order={order.pk}",
                    "platform": (
                        order.conversation.integration.platform
                        if order.conversation_id
                        else ""
                    ),
                    "status": order.status,
                }
            )

        messages = (
            Message.objects.filter(conversation__integration__user=self.request.user)
            .filter(text__icontains=query)
            .select_related("conversation__integration", "conversation__contact")
            .order_by("-external_created_at", "-created_at")[:5]
        )
        for message in messages:
            contact = message.conversation.contact
            title = (
                contact.name
                or (f"@{contact.username}" if contact.username else "")
                or "Паём"
            )
            results.append(
                {
                    "type": "message",
                    "id": message.pk,
                    "title": title,
                    "subtitle": message.text[:140] or "Паёми бе матн",
                    "url": f"/messages?conversation={message.conversation_id}",
                    "platform": message.conversation.integration.platform,
                }
            )

        return Response({"query": query, "results": results})


class AISuggestionsView(APIView):
    serializer_class = AISuggestionsRequestSerializer

    @extend_schema(
        request=AISuggestionsRequestSerializer,
        responses={200: AISuggestionsResponseSerializer, 500: OpenApiTypes.OBJECT},
        tags=["ai"],
    )
    def post(self, request):
        text = str(request.data.get("text") or "").strip()
        if not text:
            return Response({"suggestions": []})
        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            return Response({"error": "OPENROUTER_API_KEY is not configured."}, status=500)
        try:
            payload = json.dumps({
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ту ёвари бизнес ҳастӣ. ба паёми муштарӣ ба забони тоҷикӣ 3 ҷавоби кӯтоҳ ва табиии пешниҳод кун. Ҷавобҳо бояд кӯтоҳ (1-2 ҷумла), дӯстона ва касбӣ бошанд. Танҳо 3 ҷавоб баргардон, як stereotype накун, бе шумора ё bullet. Ҷавобҳоро бо \\n---\\n ҷудо кун.",
                    },
                    {"role": "user", "content": text},
                ],
                "max_tokens": 300,
            }).encode("utf-8")
            req = Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            suggestions = [s.strip() for s in content.split("\n---\n") if s.strip()][:3]
            return Response({"suggestions": suggestions})
        except Exception as exc:
            return Response({"error": str(exc)}, status=500)

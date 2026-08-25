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
            facebook=Count(
                "id",
                filter=Q(conversation__integration__platform="facebook"),
            ),
            viber=Count(
                "id",
                filter=Q(conversation__integration__platform="viber"),
            ),
            vk=Count(
                "id",
                filter=Q(conversation__integration__platform="vk"),
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
                "facebook_messages": message_counts["facebook"],
                "viber_messages": message_counts["viber"],
                "vk_messages": message_counts["vk"],
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

        def fallback_suggestions(value):
            lowered = value.lower()
            if any(word in lowered for word in ("нарх", "цена", "price", "стоимость")):
                return [
                    "Салом! Нарх ва шартҳои фармоишро барои шумо мефиристем.",
                    "Лутфан маҳсулот ва миқдори лозимаро нависед, то ҳисоб кунем.",
                    "Мо ҳозир нарх ва вақти расониданро санҷида ҷавоб медиҳем.",
                ]
            if any(word in lowered for word in ("салом", "hello", "hi", "ассалом")):
                return [
                    "Салом! Хуш омадед. Чӣ кӯмак карда метавонем?",
                    "Салом! Саволи шуморо бо хурсандӣ ҷавоб медиҳем.",
                    "Салом! Лутфан маълумоти лозимаро нависед.",
                ]
            return [
                "Ташаккур барои паём. Мо онро санҷида, зуд ҷавоб медиҳем.",
                "Маълумоти шуморо гирифтем. Лутфан каме интизор шавед.",
                "Барои кӯмаки беҳтар, тафсилоти бештар мефиристед?",
            ]

        groq_key = getattr(settings, "GROQ_API_KEY", "")
        openrouter_key = settings.OPENROUTER_API_KEY
        api_key = groq_key or openrouter_key
        if not api_key:
            return Response({"suggestions": fallback_suggestions(text), "source": "local"})
        try:
            is_groq = bool(groq_key)
            payload = json.dumps({
                "model": settings.GROQ_MODEL if is_groq else settings.OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Ту ёвари бизнес ҳастӣ. ба паёми муштарӣ ба забони тоҷикӣ 3 ҷавоби кӯтоҳ ва табиии пешниҳод кун. Ҷавобҳо бояд кӯтоҳ (1-2 ҷумла), дӯстона ва касбӣ бошанд. Танҳо 3 ҷавоб баргардон, як stereotype накун, бе шумора ё bullet. Ҷавобҳоро бо \\n---\\n ҷудо кун.",
                    },
                    {"role": "user", "content": text},
                ],
                "max_tokens": 300,
            }).encode("utf-8")
            endpoint = "https://api.groq.com/openai/v1/chat/completions" if is_groq else "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            if not is_groq:
                headers.update({
                    "HTTP-Referer": getattr(settings, "SITE_URL", ""),
                    "X-OpenRouter-Title": "Munis Business Hub",
                })
            req = Request(endpoint, data=payload, headers=headers, method="POST")
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            suggestions = [s.strip(" -*\t") for s in content.split("\n---\n") if s.strip()][:3]
            if not suggestions:
                suggestions = fallback_suggestions(text)
            return Response({"suggestions": suggestions})
        except Exception as exc:
            return Response({"suggestions": fallback_suggestions(text), "source": "local", "error": str(exc)})


class AITranslateView(APIView):
    def post(self, request):
        text = str(request.data.get("text") or "").strip()
        language = str(request.data.get("language") or "tg").lower()
        languages = {"tg": "Tajik", "ru": "Russian", "en": "English"}
        if not text or language not in languages:
            return Response({"translation": text})
        key = getattr(settings, "GROQ_API_KEY", "") or getattr(settings, "OPENROUTER_API_KEY", "")
        is_groq = bool(getattr(settings, "GROQ_API_KEY", ""))
        if key:
            endpoint = "https://api.groq.com/openai/v1/chat/completions" if is_groq else "https://openrouter.ai/api/v1/chat/completions"
            model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile") if is_groq else getattr(settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini")
            payload = json.dumps({"model": model, "messages": [{"role": "system", "content": f"Translate the message to {languages[language]}. Return only the translation, preserving the meaning and tone."}, {"role": "user", "content": text}], "max_tokens": 300}).encode("utf-8")
            try:
                response = urlopen(Request(endpoint, data=payload, headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}, method="POST"), timeout=20)
                translation = json.loads(response.read().decode("utf-8")).get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if translation:
                    return Response({"translation": translation, "language": language})
            except Exception:
                pass
        common = {
            "Салом!": {"tg": "Салом!", "ru": "Здравствуйте!", "en": "Hello!"},
            "Салом! Хуш омадед. Саволатонро нависед, ман кӯмак мекунам.": {
                "tg": "Салом! Хуш омадед. Саволатонро нависед, ман кӯмак мекунам.",
                "ru": "Здравствуйте! Добро пожаловать. Напишите свой вопрос, и я помогу.",
                "en": "Hello! Welcome. Write your question and I will help you.",
            },
        }
        if text in common:
            return Response({"translation": common[text][language], "language": language, "source": "local"})
        return Response({"translation": text, "language": language, "source": "original"})

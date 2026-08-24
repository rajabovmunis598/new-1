from django.db.models import Case, Count, IntegerField, Q, When
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Conversation, ConversationNote
from .serializers import (
    ConversationNoteSerializer,
    ConversationReadResponseSerializer,
    ConversationSerializer,
    ConversationSnoozeSerializer,
)


class ConversationViewSet(ModelViewSet):
    queryset = Conversation.objects.none()
    serializer_class = ConversationSerializer
    http_method_names = ("get", "patch", "post", "head", "options")
    filterset_fields = (
        "status",
        "contact",
        "integration",
        "is_pinned",
        "priority",
    )
    search_fields = (
        "title",
        "contact__name",
        "contact__username",
        "contact__phone",
    )
    ordering_fields = (
        "created_at",
        "updated_at",
        "last_message_at",
        "is_pinned",
        "priority",
        "snoozed_until",
    )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "platform",
                str,
                OpenApiParameter.QUERY,
                description="Filter by integration platform.",
            ),
            OpenApiParameter(
                "date_from",
                str,
                OpenApiParameter.QUERY,
                description="Filter conversations created at or after this ISO datetime.",
            ),
            OpenApiParameter(
                "date_to",
                str,
                OpenApiParameter.QUERY,
                description="Filter conversations created at or before this ISO datetime.",
            ),
            OpenApiParameter(
                "snoozed",
                bool,
                OpenApiParameter.QUERY,
                description="True for actively snoozed; false for due or unsnoozed.",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            Conversation.objects.filter(integration__user=self.request.user)
            .select_related("integration", "contact")
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=Q(
                        messages__is_read=False,
                        messages__sender_type="customer",
                    ),
                ),
                priority_rank=Case(
                    When(priority="low", then=0),
                    When(priority="normal", then=1),
                    When(priority="high", then=2),
                    When(priority="urgent", then=3),
                    default=1,
                    output_field=IntegerField(),
                ),
            )
        )
        params = self.request.query_params
        platform = params.get("platform")
        if platform:
            queryset = queryset.filter(integration__platform=platform)
        if params.get("date_from"):
            queryset = queryset.filter(created_at__gte=params["date_from"])
        if params.get("date_to"):
            queryset = queryset.filter(created_at__lte=params["date_to"])

        snoozed = params.get("snoozed")
        if snoozed is not None:
            normalized = snoozed.strip().lower()
            if normalized in {"true", "1"}:
                queryset = queryset.filter(snoozed_until__gt=timezone.now())
            elif normalized in {"false", "0"}:
                queryset = queryset.filter(
                    Q(snoozed_until__isnull=True)
                    | Q(snoozed_until__lte=timezone.now())
                )
            else:
                raise ValidationError({"snoozed": "Use true/false or 1/0."})
        return queryset.order_by("-is_pinned", "-last_message_at", "-id")

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        requested = self.request.query_params.get("ordering")
        if not requested:
            return queryset
        ordering = []
        allowed = set(self.ordering_fields)
        for term in requested.split(","):
            term = term.strip()
            field = term.removeprefix("-")
            if field not in allowed:
                continue
            if field == "priority":
                field = "priority_rank"
            ordering.append(f"-{field}" if term.startswith("-") else field)
        return queryset.order_by(*ordering) if ordering else queryset

    @extend_schema(request=None, responses={200: ConversationSerializer})
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._set_fields(status="closed")

    @extend_schema(request=None, responses={200: ConversationSerializer})
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._set_fields(status="archived")

    @extend_schema(
        request=None,
        responses={200: ConversationReadResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        conversation = self.get_object()
        updated = conversation.messages.filter(
            sender_type="customer",
            is_read=False,
        ).update(is_read=True)
        return Response({"updated": updated, "unread_count": 0})

    @extend_schema(request=None, responses={200: ConversationSerializer})
    @action(detail=True, methods=["post"])
    def pin(self, request, pk=None):
        return self._set_fields(is_pinned=True)

    @extend_schema(request=None, responses={200: ConversationSerializer})
    @action(detail=True, methods=["post"])
    def unpin(self, request, pk=None):
        return self._set_fields(is_pinned=False)

    @extend_schema(
        request=ConversationSnoozeSerializer,
        responses={200: ConversationSerializer},
    )
    @action(detail=True, methods=["post"])
    def snooze(self, request, pk=None):
        serializer = ConversationSnoozeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._set_fields(
            snoozed_until=serializer.validated_data["snoozed_until"]
        )

    @extend_schema(request=None, responses={200: ConversationSerializer})
    @action(detail=True, methods=["post"])
    def unsnooze(self, request, pk=None):
        return self._set_fields(snoozed_until=None)

    def _set_fields(self, **values):
        conversation = self.get_object()
        for field, value in values.items():
            setattr(conversation, field, value)
        conversation.save(update_fields=[*values, "updated_at"])
        return Response(self.get_serializer(conversation).data)


class ConversationNoteListCreateView(generics.ListCreateAPIView):
    queryset = ConversationNote.objects.none()
    serializer_class = ConversationNoteSerializer

    def get_conversation(self):
        if not hasattr(self, "_conversation"):
            self._conversation = get_object_or_404(
                Conversation.objects.select_related("integration"),
                pk=self.kwargs["conversation_pk"],
                integration__user=self.request.user,
            )
        return self._conversation

    def get_queryset(self):
        return ConversationNote.objects.filter(
            conversation=self.get_conversation()
        ).select_related("author")

    def perform_create(self, serializer):
        serializer.save(
            conversation=self.get_conversation(),
            author=self.request.user,
        )


class ConversationNoteDestroyView(generics.DestroyAPIView):
    queryset = ConversationNote.objects.none()
    serializer_class = ConversationNoteSerializer
    lookup_url_kwarg = "note_id"
    http_method_names = ("delete", "head", "options")

    def get_queryset(self):
        return ConversationNote.objects.filter(
            conversation_id=self.kwargs["conversation_pk"],
            conversation__integration__user=self.request.user,
            author=self.request.user,
        )

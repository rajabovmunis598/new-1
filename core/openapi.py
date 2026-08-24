from rest_framework import serializers

from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import OpenApiResponse, extend_schema
from users.serializers import LoginSerializer, RegisterSerializer, UserSerializer


class TokenPairResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class LoginResponseSerializer(serializers.Serializer):
    user = UserSerializer(read_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class RegisterResponseSerializer(UserSerializer):
    tokens = TokenPairResponseSerializer(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("tokens",)
        read_only_fields = fields


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class DashboardStatisticsSerializer(serializers.Serializer):
    total_messages = serializers.IntegerField(read_only=True)
    unread_messages = serializers.IntegerField(read_only=True)
    telegram_messages = serializers.IntegerField(read_only=True)
    whatsapp_messages = serializers.IntegerField(read_only=True)
    instagram_messages = serializers.IntegerField(read_only=True)
    total_conversations = serializers.IntegerField(read_only=True)
    open_conversations = serializers.IntegerField(read_only=True)
    total_orders = serializers.IntegerField(read_only=True)
    new_orders = serializers.IntegerField(read_only=True)
    completed_orders = serializers.IntegerField(read_only=True)


class ExternalURLResponseSerializer(serializers.Serializer):
    url = serializers.URLField(read_only=True, allow_null=True)


class GlobalSearchResultSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=("contact", "conversation", "order", "message"),
        read_only=True,
    )
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    subtitle = serializers.CharField(read_only=True)
    url = serializers.CharField(read_only=True)
    platform = serializers.CharField(read_only=True, allow_blank=True)
    status = serializers.CharField(read_only=True, required=False)


class GlobalSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField(read_only=True)
    results = GlobalSearchResultSerializer(many=True, read_only=True)


class AISuggestionsRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000, write_only=True)


class AISuggestionsResponseSerializer(serializers.Serializer):
    suggestions = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )


class LoginViewSchema(OpenApiViewExtension):
    target_class = "users.views.LoginView"

    def view_replacement(self):
        class Fixed(self.target_class):
            @extend_schema(
                request=LoginSerializer,
                responses={200: LoginResponseSerializer},
                tags=["auth"],
            )
            def post(self, request, *args, **kwargs):
                pass  # pragma: no cover

        return Fixed


class RegisterViewSchema(OpenApiViewExtension):
    target_class = "users.views.RegisterView"

    def view_replacement(self):
        class Fixed(self.target_class):
            @extend_schema(
                request=RegisterSerializer,
                responses={201: RegisterResponseSerializer},
                tags=["auth"],
            )
            def post(self, request, *args, **kwargs):
                pass  # pragma: no cover

        return Fixed


class LogoutViewSchema(OpenApiViewExtension):
    target_class = "users.views.LogoutView"

    def view_replacement(self):
        class Fixed(self.target_class):
            @extend_schema(
                request=LogoutRequestSerializer,
                responses={
                    204: None,
                    400: OpenApiResponse(description="Invalid refresh token."),
                },
                tags=["auth"],
            )
            def post(self, request, *args, **kwargs):
                pass  # pragma: no cover

        return Fixed


class DashboardStatisticsViewSchema(OpenApiViewExtension):
    target_class = "core.views.DashboardStatisticsView"

    def view_replacement(self):
        class Fixed(self.target_class):
            @extend_schema(
                responses={200: DashboardStatisticsSerializer},
                tags=["dashboard"],
            )
            def get(self, request, *args, **kwargs):
                pass  # pragma: no cover

        return Fixed


class ExternalURLViewSchema(OpenApiViewExtension):
    target_class = "messages.views.ExternalURLView"

    def view_replacement(self):
        class Fixed(self.target_class):
            @extend_schema(
                responses={200: ExternalURLResponseSerializer},
                tags=["messages"],
            )
            def get(self, request, *args, **kwargs):
                pass  # pragma: no cover

        return Fixed

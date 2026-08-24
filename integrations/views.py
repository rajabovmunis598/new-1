import asyncio
import hashlib
import logging
import json
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from audit.models import IntegrationEvent

from .models import Integration
from .security import verify_meta_signature
from .serializers import (
    FacebookOAuthCallbackSerializer,
    FacebookOAuthStartResponseSerializer,
    FacebookOAuthStartSerializer,
    InstagramOAuthCallbackSerializer,
    InstagramOAuthStartResponseSerializer,
    InstagramOAuthStartSerializer,
    IntegrationIDSerializer,
    IntegrationSerializer,
    Telegram2FASerializer,
    TelegramStartResponseSerializer,
    TelegramStartSerializer,
    TelegramVerifyResponseSerializer,
    TelegramVerifySerializer,
    WhatsAppConnectSerializer,
    WhatsAppTestResponseSerializer,
)
from .services import get_adapter
from .services.facebook_messenger import FacebookGraphClient, FacebookAPIError
from .services.instagram_api import InstagramAPIClient, InstagramAPIError


INSTAGRAM_OAUTH_STATE_SALT = "integrations.instagram.oauth-state"
INSTAGRAM_OAUTH_BROWSER_SALT = "integrations.instagram.oauth-browser"

FACEBOOK_OAUTH_STATE_SALT = "integrations.facebook.oauth-state"
FACEBOOK_OAUTH_BROWSER_SALT = "integrations.facebook.oauth-browser"

logger = logging.getLogger(__name__)


def _instagram_redirect_uri(request):
    configured = str(getattr(settings, "INSTAGRAM_REDIRECT_URI", "")).strip()
    if configured:
        return configured
    if settings.DEBUG:
        return request.build_absolute_uri(reverse("instagram-oauth-callback"))
    raise ValidationError(
        "INSTAGRAM_REDIRECT_URI must be configured on the server."
    )


def _validate_instagram_server_config():
    if not str(getattr(settings, "INSTAGRAM_VERIFY_TOKEN", "")).strip():
        raise ValidationError(
            "INSTAGRAM_VERIFY_TOKEN must be configured on the server."
        )


def _instagram_state_cache_key(state):
    digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
    return f"instagram_oauth_state:{digest}"


def _instagram_browser_cookie_name(state):
    digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
    return f"instagram_oauth_{digest[:24]}"


def _instagram_browser_cookie_value(state):
    state_digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
    return salted_hmac(
        INSTAGRAM_OAUTH_BROWSER_SALT,
        state_digest,
        algorithm="sha256",
    ).hexdigest()


def _instagram_callback_path():
    return reverse("instagram-oauth-callback")


def _new_instagram_oauth_state(user, name, app_id=None, app_secret=None, verify_token=None):
    ttl = settings.INSTAGRAM_OAUTH_STATE_TTL
    payload = {
        "user_id": user.pk,
        "name": name,
        "nonce": secrets.token_urlsafe(24),
    }
    if app_id:
        payload["app_id"] = app_id
    if app_secret:
        payload["app_secret"] = app_secret
    if verify_token:
        payload["verify_token"] = verify_token
    for _ in range(3):
        state = signing.dumps(
            payload,
            salt=INSTAGRAM_OAUTH_STATE_SALT,
            compress=True,
        )
        if cache.add(_instagram_state_cache_key(state), True, timeout=ttl):
            return state
    raise ValidationError("Instagram authorization could not be started.")


def _load_instagram_oauth_state(state):
    payload = signing.loads(
        state,
        salt=INSTAGRAM_OAUTH_STATE_SALT,
        max_age=settings.INSTAGRAM_OAUTH_STATE_TTL,
    )
    if not isinstance(payload, dict) or not payload.get("nonce"):
        raise signing.BadSignature("Invalid Instagram OAuth state")
    return payload


def _consume_instagram_oauth_state(state, payload=None):
    payload = payload or _load_instagram_oauth_state(state)
    if not cache.delete(_instagram_state_cache_key(state)):
        raise signing.BadSignature("Expired or already used Instagram OAuth state")
    return payload


def _validate_instagram_browser_binding(request, state):
    supplied = str(
        request.COOKIES.get(_instagram_browser_cookie_name(state)) or ""
    )
    expected = _instagram_browser_cookie_value(state)
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise signing.BadSignature("Invalid Instagram OAuth browser binding")


def _instagram_result_redirect(result, state=None):
    response = HttpResponseRedirect(
        f"/integrations?{urlencode({'instagram': result})}"
    )
    if state:
        response.delete_cookie(
            _instagram_browser_cookie_name(state),
            path=_instagram_callback_path(),
            samesite="Lax",
        )
    return response


def _dispatch_instagram_event(event_id):
    from .tasks import process_instagram_event

    try:
        process_instagram_event.delay(event_id)
    except Exception:
        IntegrationEvent.objects.filter(pk=event_id).update(
            status="failed",
            error_message="Instagram event task dispatch failed.",
        )
        raise


def _facebook_redirect_uri(request):
    configured = str(getattr(settings, "FACEBOOK_REDIRECT_URI", "")).strip()
    if configured:
        return configured
    if settings.DEBUG:
        return request.build_absolute_uri(reverse("facebook-oauth-callback"))
    raise ValidationError(
        "FACEBOOK_REDIRECT_URI must be configured on the server."
    )


def _facebook_state_cache_key(state):
    digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
    return f"facebook_oauth_state:{digest}"


def _facebook_browser_cookie_name(state):
    digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
    return f"facebook_oauth_{digest[:24]}"


def _facebook_browser_cookie_value(state):
    state_digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
    return salted_hmac(
        FACEBOOK_OAUTH_BROWSER_SALT,
        state_digest,
        algorithm="sha256",
    ).hexdigest()


def _facebook_callback_path():
    return reverse("facebook-oauth-callback")


def _new_facebook_oauth_state(user, name, app_id=None, app_secret=None, verify_token=None):
    ttl = getattr(settings, "FACEBOOK_OAUTH_STATE_TTL", 600)
    payload = {
        "user_id": user.pk,
        "name": name,
        "nonce": secrets.token_urlsafe(24),
    }
    if app_id:
        payload["app_id"] = app_id
    if app_secret:
        payload["app_secret"] = app_secret
    if verify_token:
        payload["verify_token"] = verify_token
    for _ in range(3):
        state = signing.dumps(
            payload,
            salt=FACEBOOK_OAUTH_STATE_SALT,
            compress=True,
        )
        if cache.add(_facebook_state_cache_key(state), True, timeout=ttl):
            return state
    raise ValidationError("Facebook authorization could not be started.")


def _load_facebook_oauth_state(state):
    ttl = getattr(settings, "FACEBOOK_OAUTH_STATE_TTL", 600)
    payload = signing.loads(
        state,
        salt=FACEBOOK_OAUTH_STATE_SALT,
        max_age=ttl,
    )
    if not isinstance(payload, dict) or not payload.get("nonce"):
        raise signing.BadSignature("Invalid Facebook OAuth state")
    return payload


def _consume_facebook_oauth_state(state, payload=None):
    payload = payload or _load_facebook_oauth_state(state)
    if not cache.delete(_facebook_state_cache_key(state)):
        raise signing.BadSignature("Expired or already used Facebook OAuth state")
    return payload


def _validate_facebook_browser_binding(request, state):
    supplied = str(
        request.COOKIES.get(_facebook_browser_cookie_name(state)) or ""
    )
    expected = _facebook_browser_cookie_value(state)
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise signing.BadSignature("Invalid Facebook OAuth browser binding")


def _facebook_result_redirect(result, state=None):
    response = HttpResponseRedirect(
        f"/integrations?{urlencode({'facebook': result})}"
    )
    if state:
        response.delete_cookie(
            _facebook_browser_cookie_name(state),
            path=_facebook_callback_path(),
            samesite="Lax",
        )
    return response


def _dispatch_facebook_event(event_id):
    from .tasks import process_facebook_event

    try:
        process_facebook_event.delay(event_id)
    except Exception:
        IntegrationEvent.objects.filter(pk=event_id).update(
            status="failed",
            error_message="Facebook event task dispatch failed.",
        )
        raise


class IntegrationViewSet(viewsets.ModelViewSet):
    queryset = Integration.objects.none()
    serializer_class = IntegrationSerializer
    http_method_names = ("get", "patch", "delete", "head", "options")
    filterset_fields = ("platform", "status")
    def get_queryset(self):
        return Integration.objects.filter(user=self.request.user)


class TelegramStartView(APIView):
    serializer_class = TelegramStartSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_start"

    @extend_schema(responses={201: TelegramStartResponseSerializer})
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        obj = Integration(
            user=request.user,
            platform="telegram",
            name=data["name"],
            status="pending",
        )
        obj.set_credentials({"api_id": data["api_id"], "api_hash": data["api_hash"]})
        obj.save()
        try:
            asyncio.run(get_adapter(obj).start(data["phone"]))
        except Exception:
            obj.delete()
            raise
        return Response(
            {"integration_id": obj.id, "status": "code_sent"},
            status=201,
        )


class TelegramVerifyView(APIView):
    serializer_class = TelegramVerifySerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_verify"

    @extend_schema(responses={200: TelegramVerifyResponseSerializer})
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = get_object_or_404(
            Integration,
            id=serializer.validated_data["integration_id"],
            user=request.user,
            platform="telegram",
        )
        result = asyncio.run(
            get_adapter(obj).verify(serializer.validated_data["code"])
        )
        return Response({"integration": IntegrationSerializer(obj).data, **result})


class Telegram2FAView(APIView):
    serializer_class = Telegram2FASerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_2fa"

    @extend_schema(responses={200: IntegrationSerializer})
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = get_object_or_404(
            Integration,
            id=serializer.validated_data["integration_id"],
            user=request.user,
            platform="telegram",
        )
        asyncio.run(
            get_adapter(obj).verify_2fa(serializer.validated_data["password"])
        )
        return Response(IntegrationSerializer(obj).data)


class PlatformDisconnectView(APIView):
    platform = None
    serializer_class = IntegrationIDSerializer

    @extend_schema(request=IntegrationIDSerializer, responses={204: None})
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = get_object_or_404(
            Integration,
            id=serializer.validated_data["integration_id"],
            user=request.user,
            platform=self.platform,
        )
        get_adapter(obj).disconnect()
        return Response(status=204)


class TelegramStatusView(APIView):
    serializer_class = IntegrationSerializer

    @extend_schema(responses={200: IntegrationSerializer})
    def get(self, request):
        obj = Integration.objects.filter(user=request.user, platform="telegram").first()
        return Response(
            IntegrationSerializer(obj).data if obj else {"status": "inactive"}
        )


class InstagramOAuthStartView(APIView):
    serializer_class = InstagramOAuthStartSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "instagram_oauth_start"

    @extend_schema(
        request=InstagramOAuthStartSerializer,
        responses={200: InstagramOAuthStartResponseSerializer},
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _validate_instagram_server_config()
        redirect_uri = _instagram_redirect_uri(request)
        # App credentials are configured once by the administrator. Optional
        # request values remain supported for backward compatibility, but
        # ordinary users no longer need to enter secrets in the UI.
        app_id = data.get("app_id") or settings.INSTAGRAM_APP_ID
        app_secret = data.get("app_secret") or settings.INSTAGRAM_APP_SECRET
        verify_token = data.get("verify_token") or settings.INSTAGRAM_VERIFY_TOKEN
        client = InstagramAPIClient(app_id=app_id, app_secret=app_secret)
        client.require_app_credentials()
        state = _new_instagram_oauth_state(
            request.user,
            data["name"],
            app_id=app_id,
            app_secret=app_secret,
            verify_token=verify_token,
        )
        try:
            authorization_url = client.authorization_url(
                redirect_uri=redirect_uri,
                state=state,
            )
        except Exception:
            cache.delete(_instagram_state_cache_key(state))
            raise
        response = Response(
            {
                "authorization_url": authorization_url,
                "expires_in": settings.INSTAGRAM_OAUTH_STATE_TTL,
            }
        )
        response.set_cookie(
            _instagram_browser_cookie_name(state),
            _instagram_browser_cookie_value(state),
            max_age=settings.INSTAGRAM_OAUTH_STATE_TTL,
            path=_instagram_callback_path(),
            secure=not settings.DEBUG,
            httponly=True,
            samesite="Lax",
        )
        return response


class InstagramOAuthCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = InstagramOAuthCallbackSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("code", str, OpenApiParameter.QUERY),
            OpenApiParameter("state", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("error", str, OpenApiParameter.QUERY),
        ],
        responses={302: None},
    )
    def get(self, request):
        raw_state = str(request.query_params.get("state") or "")
        serializer = self.serializer_class(data=request.query_params)
        if not serializer.is_valid():
            return _instagram_result_redirect("error", raw_state)

        data = serializer.validated_data
        try:
            state = _load_instagram_oauth_state(data["state"])
            _validate_instagram_browser_binding(request, data["state"])
            state = _consume_instagram_oauth_state(data["state"], state)
            if data.get("error") or not data.get("code"):
                raise ValidationError("Instagram authorization was denied.")

            user = get_user_model().objects.get(
                pk=state["user_id"],
                is_active=True,
            )
            redirect_uri = _instagram_redirect_uri(request)
            client = InstagramAPIClient(
                app_id=state.get("app_id"),
                app_secret=state.get("app_secret"),
            )
            token_data = client.exchange_code(
                code=data["code"],
                redirect_uri=redirect_uri,
            )
            access_token = str(token_data.get("access_token") or "")
            profile = client.get_own_profile(access_token)
            account_id = str(
                profile.get("user_id") or token_data.get("user_id") or ""
            )
            if not access_token or not account_id.isdigit():
                raise InstagramAPIError(
                    "Instagram authorization response is incomplete."
                )

            active_owner = Integration.objects.filter(
                platform="instagram",
                status="active",
                external_account_id=account_id,
            ).only("user_id").first()
            if active_owner and active_owner.user_id != user.pk:
                raise ValidationError(
                    "This Instagram account is already connected."
                )

            client.subscribe_webhooks(
                account_id=account_id,
                access_token=access_token,
            )
            expires_in = int(token_data.get("expires_in") or 0)
            credentials = {
                "access_token": access_token,
                "instagram_user_id": account_id,
                "username": str(profile.get("username") or ""),
                "app_id": state.get("app_id", ""),
                "app_secret": state.get("app_secret", ""),
                "verify_token": state.get("verify_token", ""),
            }
            if expires_in > 0:
                credentials["expires_at"] = (
                    timezone.now() + timedelta(seconds=expires_in)
                ).isoformat()

            with transaction.atomic():
                owned_integrations = (
                    Integration.objects.select_for_update()
                    .filter(
                        user=user,
                        platform="instagram",
                        external_account_id=account_id,
                    )
                )
                integration = owned_integrations.filter(status="active").first()
                if integration is None:
                    integration = owned_integrations.order_by("-updated_at").first()
                if integration is None:
                    integration = Integration(
                        user=user,
                        platform="instagram",
                        external_account_id=account_id,
                    )
                integration.name = state["name"]
                integration.status = "active"
                integration.last_error = ""
                integration.last_sync_at = timezone.now()
                integration.webhook_url = request.build_absolute_uri(
                    reverse("instagram-webhook")
                )
                integration.set_credentials(credentials)
                integration.save()
        except (
            IntegrityError,
            InstagramAPIError,
            KeyError,
            TypeError,
            ValueError,
            ValidationError,
            get_user_model().DoesNotExist,
            signing.BadSignature,
        ) as exc:
            # Keep the browser response generic, but preserve a sanitized
            # server-side reason for diagnosing Meta redirect/permission/API
            # failures. Credentials and OAuth codes are never logged here.
            logger.warning(
                "Instagram OAuth callback failed: %s%s",
                type(exc).__name__,
                f" (status={exc.status_code})"
                if isinstance(exc, InstagramAPIError) and exc.status_code
                else "",
            )
            return _instagram_result_redirect("error", raw_state)

        return _instagram_result_redirect("connected", raw_state)


class WhatsAppConnectView(APIView):
    serializer_class = WhatsAppConnectSerializer

    @extend_schema(responses={201: IntegrationSerializer})
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        obj = Integration(
            user=request.user,
            platform="whatsapp",
            name=data.pop("name"),
            status="active",
            external_account_id=data["phone_number_id"],
        )
        obj.set_credentials(data)
        obj.save()
        obj.webhook_url = request.build_absolute_uri(
            reverse("whatsapp-webhook", kwargs={"integration_id": obj.pk})
        )
        obj.save(update_fields=["webhook_url", "updated_at"])
        return Response(
            IntegrationSerializer(obj, context={"request": request}).data,
            status=201,
        )


class WhatsAppTestView(APIView):
    serializer_class = IntegrationIDSerializer

    @extend_schema(
        request=IntegrationIDSerializer,
        responses={200: WhatsAppTestResponseSerializer},
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = get_object_or_404(
            Integration,
            id=serializer.validated_data["integration_id"],
            user=request.user,
            platform="whatsapp",
        )
        return Response(
            {
                "ok": bool(obj.get_credentials().get("access_token")),
                "status": obj.status,
            }
        )


class WhatsAppWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get_integration(self, integration_id):
        return get_object_or_404(
            Integration,
            id=integration_id,
            platform="whatsapp",
            status="active",
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("hub.mode", str, OpenApiParameter.QUERY),
            OpenApiParameter("hub.verify_token", str, OpenApiParameter.QUERY),
            OpenApiParameter("hub.challenge", str, OpenApiParameter.QUERY),
        ],
        responses={200: OpenApiTypes.STR, 403: OpenApiTypes.OBJECT},
    )
    def get(self, request, integration_id):
        integration = self.get_integration(integration_id)
        token = request.query_params.get("hub.verify_token")
        expected_token = str(integration.get_credentials().get("verify_token", ""))
        if (
            request.query_params.get("hub.mode") == "subscribe"
            and token
            and expected_token
            and secrets.compare_digest(token, expected_token)
        ):
            return HttpResponse(
                request.query_params.get("hub.challenge", ""),
                content_type="text/plain",
            )
        return Response({"detail": "Verification failed"}, status=403)

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def post(self, request, integration_id):
        integration = self.get_integration(integration_id)
        secret = str(integration.get_credentials().get("app_secret", ""))
        if not verify_meta_signature(
            request.body,
            request.headers.get("X-Hub-Signature-256"),
            secret,
        ):
            return Response({"detail": "Invalid signature"}, status=403)
        accepted = 0
        from .tasks import _process_whatsapp_event, process_whatsapp_event
        for entry in request.data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                phone_id = value.get("metadata", {}).get("phone_number_id")
                if str(phone_id) != integration.external_account_id:
                    continue
                for msg in value.get("messages", []):
                    event_id = msg.get("id", "")
                    event, created = IntegrationEvent.objects.get_or_create(
                        integration=integration,
                        external_event_id=event_id,
                        defaults={
                            "event_type": "message",
                            "payload": {
                                "message": msg,
                                "contacts": value.get("contacts", []),
                            },
                        },
                    )
                    if created:
                        accepted += 1
                        try:
                            # Process synchronously so the message is persisted
                            # immediately, even when no Celery worker runs.
                            _process_whatsapp_event(event.id)
                        except Exception:
                            # On failure, hand the event to Celery for a delayed
                            # retry; retry_failed_event beat also re-queues it.
                            try:
                                process_whatsapp_event.delay(event.id)
                            except Exception:
                                pass
        return Response({"accepted": accepted})


class InstagramWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        parameters=[
            OpenApiParameter("hub.mode", str, OpenApiParameter.QUERY),
            OpenApiParameter("hub.verify_token", str, OpenApiParameter.QUERY),
            OpenApiParameter("hub.challenge", str, OpenApiParameter.QUERY),
        ],
        responses={200: OpenApiTypes.STR, 403: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        supplied_token = str(request.query_params.get("hub.verify_token") or "")
        integration_verify_tokens = Integration.objects.filter(
            platform="instagram",
            status="active",
        ).values_list("credentials", flat=True)
        expected_token = ""
        for creds in integration_verify_tokens:
            try:
                from .security import decrypt_json
                decrypted = decrypt_json(creds)
                if isinstance(decrypted, dict) and decrypted.get("verify_token"):
                    expected_token = decrypted["verify_token"]
                    break
            except Exception:
                continue
        if not expected_token:
            expected_token = str(settings.INSTAGRAM_VERIFY_TOKEN or "")
        if (
            request.query_params.get("hub.mode") == "subscribe"
            and supplied_token
            and expected_token
            and secrets.compare_digest(supplied_token, expected_token)
        ):
            return HttpResponse(
                request.query_params.get("hub.challenge", ""),
                content_type="text/plain",
            )
        return Response({"detail": "Verification failed"}, status=403)

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        body = request.body
        integration = Integration.objects.filter(
            platform="instagram",
            status="active",
        ).first()
        app_secret = settings.INSTAGRAM_APP_SECRET
        if integration:
            try:
                from .security import decrypt_json
                decrypted = decrypt_json(integration.credentials)
                if isinstance(decrypted, dict) and decrypted.get("app_secret"):
                    app_secret = decrypted["app_secret"]
            except Exception:
                pass
        if not verify_meta_signature(
            body,
            request.headers.get("X-Hub-Signature-256"),
            app_secret,
        ):
            return Response({"detail": "Invalid signature"}, status=403)

        payload = request.data
        if not isinstance(payload, dict) or payload.get("object") != "instagram":
            return Response({"accepted": 0})

        accepted = 0
        for entry in payload.get("entry") or []:
            if not isinstance(entry, dict):
                continue
            integration = Integration.objects.filter(
                platform="instagram",
                status="active",
                external_account_id=str(entry.get("id") or ""),
            ).first()
            if integration is None:
                continue
            for messaging_event in entry.get("messaging") or []:
                if not isinstance(messaging_event, dict):
                    continue
                message = messaging_event.get("message") or {}
                if not isinstance(message, dict) or message.get("is_echo"):
                    continue
                if not message and not messaging_event.get("postback"):
                    continue
                external_event_id = str(message.get("mid") or "")
                if not external_event_id:
                    canonical = json.dumps(
                        messaging_event,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                    ).encode("utf-8")
                    external_event_id = "sha256:" + hashlib.sha256(canonical).hexdigest()
                event, created = IntegrationEvent.objects.get_or_create(
                    integration=integration,
                    external_event_id=external_event_id[:255],
                    defaults={
                        "event_type": "message" if message else "postback",
                        "payload": {"messaging": messaging_event},
                    },
                )
                if created:
                    transaction.on_commit(
                        lambda event_id=event.pk: _dispatch_instagram_event(event_id)
                    )
                    accepted += 1
        return Response({"accepted": accepted})


class FacebookOAuthStartView(APIView):
    serializer_class = FacebookOAuthStartSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "facebook_oauth_start"

    @extend_schema(
        request=FacebookOAuthStartSerializer,
        responses={200: FacebookOAuthStartResponseSerializer},
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        redirect_uri = _facebook_redirect_uri(request)
        app_id = data.get("app_id") or None
        app_secret = data.get("app_secret") or None
        verify_token = data.get("verify_token") or None
        client = FacebookGraphClient(app_id=app_id, app_secret=app_secret)
        client.require_app_credentials()
        state = _new_facebook_oauth_state(
            request.user,
            data["name"],
            app_id=app_id,
            app_secret=app_secret,
            verify_token=verify_token,
        )
        try:
            authorization_url = client.authorization_url(
                redirect_uri=redirect_uri,
                state=state,
            )
        except Exception:
            cache.delete(_facebook_state_cache_key(state))
            raise
        response = Response(
            {
                "authorization_url": authorization_url,
                "expires_in": getattr(settings, "FACEBOOK_OAUTH_STATE_TTL", 600),
            }
        )
        ttl = getattr(settings, "FACEBOOK_OAUTH_STATE_TTL", 600)
        response.set_cookie(
            _facebook_browser_cookie_name(state),
            _facebook_browser_cookie_value(state),
            max_age=ttl,
            path=_facebook_callback_path(),
            secure=not settings.DEBUG,
            httponly=True,
            samesite="Lax",
        )
        return response


class FacebookOAuthCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = FacebookOAuthCallbackSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("code", str, OpenApiParameter.QUERY),
            OpenApiParameter("state", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("error", str, OpenApiParameter.QUERY),
        ],
        responses={302: None},
    )
    def get(self, request):
        raw_state = str(request.query_params.get("state") or "")
        serializer = self.serializer_class(data=request.query_params)
        if not serializer.is_valid():
            return _facebook_result_redirect("error", raw_state)

        data = serializer.validated_data
        try:
            state = _load_facebook_oauth_state(data["state"])
            _validate_facebook_browser_binding(request, data["state"])
            state = _consume_facebook_oauth_state(data["state"], state)
            if data.get("error") or not data.get("code"):
                raise ValidationError("Facebook authorization was denied.")

            user = get_user_model().objects.get(
                pk=state["user_id"],
                is_active=True,
            )
            redirect_uri = _facebook_redirect_uri(request)
            client = FacebookGraphClient(
                app_id=state.get("app_id"),
                app_secret=state.get("app_secret"),
            )
            token_data = client.exchange_code(
                code=data["code"],
                redirect_uri=redirect_uri,
            )
            access_token = str(token_data.get("access_token") or "")
            if not access_token:
                raise FacebookAPIError(
                    "Facebook authorization response is incomplete."
                )

            pages_data = client.get_pages(access_token)
            pages = pages_data.get("data", [])
            if not pages:
                raise ValidationError(
                    "No Facebook Pages found. Create a Page first."
                )

            page = pages[0]
            page_id = str(page.get("id") or "")
            page_name = str(page.get("name") or "")
            page_token = str(page.get("access_token") or access_token)

            if not page_id:
                raise FacebookAPIError("Facebook Page ID not returned.")

            client.subscribe_webhooks(
                page_id=page_id,
                access_token=page_token,
            )

            credentials = {
                "access_token": page_token,
                "page_id": page_id,
                "page_name": page_name,
                "user_access_token": access_token,
                "app_id": state.get("app_id", ""),
                "app_secret": state.get("app_secret", ""),
                "verify_token": state.get("verify_token", ""),
            }
            expires_in = int(token_data.get("expires_in") or 0)
            if expires_in > 0:
                credentials["expires_at"] = (
                    timezone.now() + timedelta(seconds=expires_in)
                ).isoformat()

            with transaction.atomic():
                owned_integrations = (
                    Integration.objects.select_for_update()
                    .filter(
                        user=user,
                        platform="facebook",
                        external_account_id=page_id,
                    )
                )
                integration = owned_integrations.filter(status="active").first()
                if integration is None:
                    integration = owned_integrations.order_by("-updated_at").first()
                if integration is None:
                    integration = Integration(
                        user=user,
                        platform="facebook",
                        external_account_id=page_id,
                    )
                integration.name = state["name"] or page_name or "Facebook"
                integration.status = "active"
                integration.last_error = ""
                integration.last_sync_at = timezone.now()
                integration.webhook_url = request.build_absolute_uri(
                    reverse("facebook-webhook")
                )
                integration.set_credentials(credentials)
                integration.save()
        except (
            IntegrityError,
            FacebookAPIError,
            KeyError,
            TypeError,
            ValueError,
            ValidationError,
            get_user_model().DoesNotExist,
            signing.BadSignature,
        ):
            return _facebook_result_redirect("error", raw_state)

        return _facebook_result_redirect("connected", raw_state)


class FacebookWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        parameters=[
            OpenApiParameter("hub.mode", str, OpenApiParameter.QUERY),
            OpenApiParameter("hub.verify_token", str, OpenApiParameter.QUERY),
            OpenApiParameter("hub.challenge", str, OpenApiParameter.QUERY),
        ],
        responses={200: OpenApiTypes.STR, 403: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        supplied_token = str(request.query_params.get("hub.verify_token") or "")
        integration_verify_tokens = Integration.objects.filter(
            platform="facebook",
            status="active",
        ).values_list("credentials", flat=True)
        expected_token = ""
        for creds in integration_verify_tokens:
            try:
                from .security import decrypt_json
                decrypted = decrypt_json(creds)
                if isinstance(decrypted, dict) and decrypted.get("verify_token"):
                    expected_token = decrypted["verify_token"]
                    break
            except Exception:
                continue
        if not expected_token:
            expected_token = str(getattr(settings, "FACEBOOK_VERIFY_TOKEN", "") or "")
        if (
            request.query_params.get("hub.mode") == "subscribe"
            and supplied_token
            and expected_token
            and secrets.compare_digest(supplied_token, expected_token)
        ):
            return HttpResponse(
                request.query_params.get("hub.challenge", ""),
                content_type="text/plain",
            )
        return Response({"detail": "Verification failed"}, status=403)

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        body = request.body
        integration = Integration.objects.filter(
            platform="facebook",
            status="active",
        ).first()
        app_secret = getattr(settings, "FACEBOOK_APP_SECRET", "")
        if integration:
            try:
                from .security import decrypt_json
                decrypted = decrypt_json(integration.credentials)
                if isinstance(decrypted, dict) and decrypted.get("app_secret"):
                    app_secret = decrypted["app_secret"]
            except Exception:
                pass
        if not verify_meta_signature(
            body,
            request.headers.get("X-Hub-Signature-256"),
            app_secret,
        ):
            return Response({"detail": "Invalid signature"}, status=403)

        payload = request.data
        if not isinstance(payload, dict) or payload.get("object") != "page":
            return Response({"accepted": 0})

        accepted = 0
        for entry in payload.get("entry") or []:
            if not isinstance(entry, dict):
                continue
            integration = Integration.objects.filter(
                platform="facebook",
                status="active",
                external_account_id=str(entry.get("id") or ""),
            ).first()
            if integration is None:
                continue
            for messaging_event in entry.get("messaging") or []:
                if not isinstance(messaging_event, dict):
                    continue
                message = messaging_event.get("message") or {}
                if not isinstance(message, dict) or message.get("is_echo"):
                    continue
                if not message and not messaging_event.get("postback"):
                    continue
                external_event_id = str(message.get("mid") or "")
                if not external_event_id:
                    canonical = json.dumps(
                        messaging_event,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                    ).encode("utf-8")
                    external_event_id = "sha256:" + hashlib.sha256(canonical).hexdigest()
                event, created = IntegrationEvent.objects.get_or_create(
                    integration=integration,
                    external_event_id=external_event_id[:255],
                    defaults={
                        "event_type": "message" if message else "postback",
                        "payload": {"messaging": messaging_event},
                    },
                )
                if created:
                    transaction.on_commit(
                        lambda event_id=event.pk: _dispatch_facebook_event(event_id)
                    )
                    accepted += 1
        return Response({"accepted": accepted})

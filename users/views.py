import hashlib
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from integrations.services.instagram_api import InstagramAPIClient, InstagramAPIError
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}

def send_welcome_email(user):
    subject = "Хуш омадед ба Munis Business Hub!"
    name = user.first_name or user.username
    message = (
        f"Салом {name}!\n\n"
        f"Шумо ба Munis Business Hub сабти ном шудед.\n\n"
        f"Акнун шумо метавонед паёмҳои Telegram, WhatsApp ва Instagram "
        f"аз як фазои корӣ идора кунед.\n\n"
        f"Бо эҳтиром,\n"
        f"Мунис Тим"
    )
    try:
        send_mail(
            subject,
            message,
            None,
            [user.email],
            fail_silently=True,
        )
    except Exception:
        pass


INSTAGRAM_LOGIN_SALT = "users.instagram.login"


def _instagram_login_key(value):
    return "instagram_login:" + hashlib.sha256(value.encode()).hexdigest()


def _instagram_login_redirect(request, **params):
    base = str(getattr(settings, "SITE_URL", "") or request.build_absolute_uri("/")).rstrip("/")
    return base + "/login?" + urlencode(params)


def _instagram_login_redirect_uri(request):
    configured = str(getattr(settings, "INSTAGRAM_REDIRECT_URI", "")).strip()
    return configured or request.build_absolute_uri("/api/integrations/instagram/connect/callback/")


class InstagramLoginStartView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        client = InstagramAPIClient()
        client.require_app_credentials()
        nonce = secrets.token_urlsafe(32)
        state = signing.dumps({"nonce": nonce}, salt=INSTAGRAM_LOGIN_SALT)
        cache.set(_instagram_login_key(state), True, timeout=600)
        redirect_uri = _instagram_login_redirect_uri(request)
        return Response({
            "authorization_url": client.authorization_url(
                redirect_uri=redirect_uri,
                state=state,
                scopes=("instagram_business_basic",),
            )
        })


class InstagramLoginCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        state = str(request.query_params.get("state") or "")
        try:
            signing.loads(state, salt=INSTAGRAM_LOGIN_SALT, max_age=600)
            if not cache.delete(_instagram_login_key(state)):
                raise signing.BadSignature("Expired Instagram login state")
            code = str(request.query_params.get("code") or "")
            if not code:
                raise signing.BadSignature("Instagram authorization was denied")
            redirect_uri = _instagram_login_redirect_uri(request)
            client = InstagramAPIClient()
            token_data = client.exchange_code(code=code, redirect_uri=redirect_uri)
            token = str(token_data.get("access_token") or "")
            profile = client.get_own_profile(token)
            instagram_id = str(profile.get("user_id") or token_data.get("user_id") or "")
            username = str(profile.get("username") or "instagram_user")[:130]
            if not instagram_id:
                raise InstagramAPIError("Instagram account information is incomplete.")
            user = User.objects.filter(instagram_user_id=instagram_id).first()
            if user is None:
                base = "ig_" + instagram_id
                candidate = base[:150]
                suffix = 1
                while User.objects.filter(username=candidate).exists():
                    candidate = (base[:140] + "_" + str(suffix))[:150]
                    suffix += 1
                user = User.objects.create_user(
                    email=f"instagram_{instagram_id}@login.local",
                    username=candidate,
                    password=secrets.token_urlsafe(32),
                    first_name=username,
                    instagram_user_id=instagram_id,
                )
            ticket = secrets.token_urlsafe(32)
            cache.set(
                _instagram_login_key(ticket),
                {"user_id": user.pk},
                timeout=120,
            )
            return Response(status=302, headers={"Location": _instagram_login_redirect(request, instagram_ticket=ticket)})
        except (signing.BadSignature, KeyError, TypeError, ValueError, InstagramAPIError):
            return Response(status=302, headers={"Location": _instagram_login_redirect(request, instagram="error")})


class InstagramLoginCompleteView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ticket = str(request.data.get("ticket") or "")
        payload = cache.get(_instagram_login_key(ticket)) if ticket else None
        if not payload or not cache.delete(_instagram_login_key(ticket)):
            return Response({"detail": "Instagram login expired. Please try again."}, status=400)
        user = User.objects.get(pk=payload["user_id"], is_active=True)
        return Response({"user": UserSerializer(user).data, **tokens_for(user)})

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    def perform_create(self, serializer):
        self.user = serializer.save()
        send_welcome_email(self.user)
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data["tokens"] = tokens_for(self.user)
        return response

class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response({"user": UserSerializer(user).data, **tokens_for(user)})

class LogoutView(APIView):
    def post(self, request):
        try:
            RefreshToken(request.data["refresh"]).blacklist()
        except Exception:
            return Response({"detail": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    def get_object(self): return self.request.user

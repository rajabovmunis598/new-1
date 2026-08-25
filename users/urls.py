from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    InstagramLoginCallbackView,
    InstagramLoginCompleteView,
    InstagramLoginStartView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("instagram/start/", InstagramLoginStartView.as_view()),
    path("instagram/callback/", InstagramLoginCallbackView.as_view(), name="instagram-login-callback"),
    path("instagram/complete/", InstagramLoginCompleteView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
]

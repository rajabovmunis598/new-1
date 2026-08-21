from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    def perform_create(self, serializer):
        self.user = serializer.save()
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

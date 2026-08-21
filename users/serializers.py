from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class RegisterSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("password",)
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    def validate(self, attrs):
        user = authenticate(email=attrs["email"], password=attrs["password"])
        if not user or not user.is_active:
            raise serializers.ValidationError("Invalid credentials")
        attrs["user"] = user
        return attrs

from rest_framework import serializers
from .models import Contact

class ContactSerializer(serializers.ModelSerializer):
    platform = serializers.CharField(source="integration.platform", read_only=True)
    class Meta:
        model = Contact
        fields = "__all__"
        read_only_fields = ("integration",)

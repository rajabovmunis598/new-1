from django.utils import timezone
from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("id", "name", "quantity", "price", "total", "metadata")
        read_only_fields = ("id", "total")

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, required=False)
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("user", "completed_at")
    def validate(self, attrs):
        request = self.context["request"]
        contact = attrs.get("contact", getattr(self.instance, "contact", None))
        conversation = attrs.get("conversation", getattr(self.instance, "conversation", None))
        if contact and contact.integration.user != request.user: raise serializers.ValidationError("Invalid contact")
        if conversation and conversation.integration.user != request.user: raise serializers.ValidationError("Invalid conversation")
        return attrs
    def create(self, data):
        items = data.pop("items", []); order = Order.objects.create(user=self.context["request"].user, **data)
        for item in items: OrderItem.objects.create(order=order, **item)
        return order
    def update(self, instance, data):
        old = instance.status; instance = super().update(instance, data)
        if instance.status == "completed" and old != "completed": instance.completed_at=timezone.now(); instance.save(update_fields=["completed_at"])
        return instance

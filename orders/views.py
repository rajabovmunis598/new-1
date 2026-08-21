from rest_framework.viewsets import ModelViewSet
from .models import Order
from .serializers import OrderSerializer

class OrderViewSet(ModelViewSet):
    queryset = Order.objects.none()
    serializer_class = OrderSerializer
    filterset_fields = ("status", "contact", "conversation", "currency")
    search_fields = ("external_id", "description", "contact__name", "contact__phone")
    ordering_fields = ("created_at", "amount", "status")
    def get_queryset(self): return Order.objects.filter(user=self.request.user).select_related("contact", "conversation").prefetch_related("items")

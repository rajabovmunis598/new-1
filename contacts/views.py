from rest_framework.viewsets import ReadOnlyModelViewSet
from .models import Contact
from .serializers import ContactSerializer

class ContactViewSet(ReadOnlyModelViewSet):
    queryset = Contact.objects.none()
    serializer_class = ContactSerializer
    filterset_fields = ("integration",)
    search_fields = ("name", "username", "phone")
    ordering_fields = ("name", "created_at")
    def get_queryset(self):
        return Contact.objects.filter(integration__user=self.request.user).select_related("integration")

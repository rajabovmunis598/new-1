from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, "user", None)
        if owner is None and hasattr(obj, "integration"):
            owner = obj.integration.user
        if owner is None and hasattr(obj, "conversation"):
            owner = obj.conversation.integration.user
        return owner == request.user

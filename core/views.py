from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView
from conversations.models import Conversation
from messages.models import Message
from orders.models import Order

class DashboardStatisticsView(APIView):
    def get(self, request):
        messages=Message.objects.filter(conversation__integration__user=request.user)
        conversations=Conversation.objects.filter(integration__user=request.user)
        orders=Order.objects.filter(user=request.user)
        m=messages.aggregate(total=Count("id"), unread=Count("id", filter=Q(is_read=False, sender_type="customer")), telegram=Count("id", filter=Q(conversation__integration__platform="telegram")), whatsapp=Count("id", filter=Q(conversation__integration__platform="whatsapp")))
        c=conversations.aggregate(total=Count("id"), opened=Count("id", filter=Q(status="open")))
        o=orders.aggregate(total=Count("id"), new=Count("id", filter=Q(status="new")), completed=Count("id", filter=Q(status="completed")))
        return Response({"total_messages":m["total"], "unread_messages":m["unread"], "telegram_messages":m["telegram"], "whatsapp_messages":m["whatsapp"], "total_conversations":c["total"], "open_conversations":c["opened"], "total_orders":o["total"], "new_orders":o["new"], "completed_orders":o["completed"]})

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from chats_app.serializers import *
from chats_app.models import Message
from rest_framework.schemas import AutoSchema
from django.db.models import Q

class LatestMessagesAPIView(APIView):
    permission_classes=[IsAuthenticated]
    """
    To retrive all the latest messages sent or received by the user
    """
    schema = AutoSchema()
    def get(self, request, *args, **kwargs):
        user = request.user
        all_messages = Message.objects.filter(Q(sender=user) | Q(receiver=user)).order_by('-message_sent_at')

        conversation_partners = set()
        last_messages = []

        for msg in all_messages:
            if msg.sender == user:
                partner = msg.receiver
            else:
                partner = msg.sender

            if partner.id not in conversation_partners:
                conversation_partners.add(partner.id)
                last_messages.append(msg)
        serializer=MessageOverviewSerializer(last_messages, many=True, context={'request': request})        
        return Response(
            {
                "message":"Latest message retrieved sucessfully",
                "data":serializer.data
            },
            status=status.HTTP_200_OK
        )
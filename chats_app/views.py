from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from chats_app.serializers import *
from chats_app.models import Message
from rest_framework.schemas import AutoSchema
from django.db.models import Q, Case, When, F, IntegerField, Max
from lugha_app.models import MyUser

from lugha_app.utils import has_active_subscription

class LatestMessagesAPIView(APIView):
    permission_classes=[IsAuthenticated]
    """
    To retrive all the latest messages sent or received by the user
    """
    schema = AutoSchema()
    def get(self, request, *args, **kwargs):
        user = request.user

        latest_message_ids = Message.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).annotate(
            partner_id=Case(
                When(sender=user, then=F('receiver')),
                When(receiver=user, then=F('sender')),
                output_field=IntegerField()
            )
        ).values('partner_id').annotate(
            latest_id=Max('id') 
        ).values_list('latest_id', flat=True)

        latest_messages = Message.objects.filter(
            id__in=latest_message_ids
        ).select_related('sender', 'receiver').order_by('-message_sent_at')

        serializer = MessageOverviewSerializer(latest_messages, many=True, context={'request': request})
        
        return Response(
            {
                "message": "Latest messages retrieved successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
    
class GetMessagesAPIView(APIView):
    permission_classes=[IsAuthenticated]
    
    """
    To retrive all the messages sent or received by the user
    """

    def get(self, request, *args, **kwargs):
        user = request.user
        partner_id = request.query_params.get('partner_id')  
        
        if not partner_id:
            return Response(
                {"message": "partner_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            partner = MyUser.objects.get(id=partner_id)
        except MyUser.DoesNotExist:
            return Response(
                {"message": "Partner user not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        messages = Message.objects.filter(
            (Q(sender=user) & Q(receiver=partner) |
            (Q(sender=partner) & Q(receiver=user))
        )).select_related('sender', 'receiver').order_by('message_sent_at')
        
        serializer = MessageOverviewSerializer(messages, many=True)
        
        return Response({
            "result_code": 0,
            "message": "Messages retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
class SendMessagesAPIView(APIView):
    permission_classes=[IsAuthenticated]

    def post(self, request, *args, **kwargs):
        student=request.user
        serializer = SendMessageSerializer(data=request.data)
        if serializer.is_valid():
            if not has_active_subscription(student):
                return Response({
                'result_code':1,
                'message': 'Sorrry, you cannot send a message unless your are subscribed to a plan'
            }, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()  
            return Response({
                'result_code':0,
                'message': 'Message created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
                'result_code':1,
                'message': 'The message could not be created',
                'data': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    


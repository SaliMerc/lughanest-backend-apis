from rest_framework import serializers
from chats_app.models import Message

class MessageOverviewSerializer(serializers.ModelSerializer):
    sender_display_name = serializers.CharField(source='sender.display_name', read_only=True)
    receiver_display_name = serializers.CharField(source='receiver.display_name', read_only=True)
    class Meta:
        model = Message
        fields = ['id', 'sender', 'receiver', 'message_content', 'message_sent_at', 'is_read', 'sender_display_name', 'receiver_display_name']

    """To return first name if teh display name is null"""
    def get_sender_display_name(self, obj):
        return obj.sender.display_name or obj.sender.first_name

    def get_receiver_display_name(self, obj):
        return obj.receiver.display_name or obj.receiver.first_name

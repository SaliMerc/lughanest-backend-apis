from rest_framework import serializers
from chats_app.models import Message

class MessageOverviewSerializer(serializers.ModelSerializer):
    sender_display_name = serializers.SerializerMethodField()
    receiver_display_name = serializers.SerializerMethodField()
    sender_profile_picture = serializers.SerializerMethodField()
    receiver_profile_picture = serializers.SerializerMethodField()
    class Meta:
        model = Message
        fields = ['id', 'sender', 'receiver', 'message_content', 'message_sent_at', 'is_read', 'sender_display_name', 'receiver_display_name', 'sender_profile_picture', 'receiver_profile_picture']

    """To return first name if the display name is null"""
    def get_sender_display_name(self, obj):
        return obj.sender.display_name or obj.sender.first_name

    def get_receiver_display_name(self, obj):
        return obj.receiver.display_name or obj.receiver.first_name
    
    def get_sender_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.sender.profile_picture and request:
            return request.build_absolute_uri(obj.sender.profile_picture.url)
        return None

    def get_receiver_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.receiver.profile_picture and request:
            return request.build_absolute_uri(obj.receiver.profile_picture.url)
        return None

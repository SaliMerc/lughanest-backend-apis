from rest_framework import serializers
from chats_app.models import Message

class MessageOverviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'

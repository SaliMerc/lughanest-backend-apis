from django.contrib import admin
from chats_app.models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'message_content','message_sent_at', 'is_read')
    list_filter = ('is_read', 'message_sent_at', 'sender', 'receiver')
    search_fields = ('message_content', 'sender__username', 'receiver__username')



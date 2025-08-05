from django.db import models
from lugha_app.models import MyUser
from django.db.models import Prefetch


# class ConversationManager(models.Manager):
#     def get_queryset(self):
#         return super().get_queryset().prefetch_related(
#             Prefetch("participants", queryset=MyUser.objects.only("id","display_name","profile_picture"))
#         )
    
# class Conversation(models.Model):
#     participants=models.ManyToManyField(MyUser, related_name="conversation")
#     created_at=models.DateTimeField(auto_now_add=True)
#     objects=ConversationManager()

#     def __str__(self):
#         participant_name=" ,".join([user.display_name for user in self.participants.all()])
#         return f"Conversation with {participant_name}"

class Message(models.Model):
    sender=models.ForeignKey(MyUser,on_delete=models.CASCADE, related_name='sender')
    receiver=models.ForeignKey(MyUser,on_delete=models.CASCADE, related_name='receiver')
    message_content=models.TextField()
    message_sent_at=models.DateTimeField(auto_now_add=True)
    is_read=models.BooleanField(default=False)

    def __str__(self):
        return self.message_content
from django.db import models
from lugha_app.models import MyUser

class Message(models.Model):
    sender=models.ForeignKey(MyUser,on_delete=models.CASCADE, related_name='sender')
    receiver=models.ForeignKey(MyUser,on_delete=models.CASCADE, related_name='receiver')
    message_content=models.TextField()
    message_sent_at=models.DateTimeField(auto_now_add=True)
    is_read=models.BooleanField(default=False)

    def __str__(self):
        return self.message_content
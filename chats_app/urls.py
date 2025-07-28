from django.urls import path,include
from .views import *

urlpatterns = [
    path('my-latest-messages/', LatestMessagesAPIView.as_view(), name='my-latest-messages'),
    path('all-my-messages/', GetMessagesAPIView.as_view(), name='all-my-messages'),
    path('create-a-message/', SendMessagesAPIView.as_view(), name='create-a message'),
]
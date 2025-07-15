from django.urls import path,include
from .views import *

urlpatterns = [
    path('my-latest-messages/', LatestMessagesAPIView.as_view(), name='my-latest-messages'),
]
from django.urls import path,include
from . import views
from .views import *

urlpatterns = [
    path('lipa-na-mpesa/', LipaNaMpesaOnlineAPIView.as_view(), name='lipa-na-mpesa'),
    path('callback/', MpesaCallbackAPIView.as_view(), name='lipa-na-mpesa-callback'),
    path('payment-data/', PaymentStatusAPIView.as_view(), name='payment-status'),
]
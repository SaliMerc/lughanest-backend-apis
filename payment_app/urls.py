from django.urls import path,include
from .views import *

urlpatterns = [
    path('lipa-na-mpesa/', LipaNaMpesaOnlineAPIView.as_view(), name='lipa-na-mpesa'),
    path('lipa-na-mpesa-callback/', MpesaCallbackAPIView.as_view(), name='lipa-na-mpesa-callback'),
    path('payment-status/', PaymentStatusAPIView.as_view(), name='payment-status'),
]
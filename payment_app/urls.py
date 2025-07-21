from django.urls import path,include
from . import views
from .views import *

urlpatterns = [
    path('lipa-na-mpesa/', LipaNaMpesaOnlineAPIView.as_view(), name='lipa-na-mpesa'),
    path('callback/', MpesaCallbackAPIView.as_view(), name='callback'),
    path('payment-data/', PaymentDataAPIView.as_view(), name='payment-status'),
    path('payment-status/', PaymentProcessingAPIView.as_view(), name='payment-status'),
]
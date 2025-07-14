from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from payment_app.serializers import TransactionsSerializer
from django.views.decorators.csrf import csrf_exempt

import requests
from datetime import datetime
import base64
from django.conf import settings
import json
from .models import Transactions
from django.contrib.auth import get_user_model

from payment_app.credentials import MpesaAccessToken, LipanaMpesaPassword,MpesaC2bCredential

from rest_framework.schemas import AutoSchema
User = get_user_model()

class LipaNaMpesaOnlineAPIView(APIView):
    """
    Handle M-Pesa online payment processing
    """

    schema = AutoSchema()

    def format_phone_number(self, phone):
        """Format phone number to 2547XXXXXXXX"""
        if phone.startswith('0'):
            return '254'+phone[1:]
        elif phone.startswith('+254'):
            return phone[1:]
        return phone
    
    def post(self, request, *args, **kwargs):
        """
        Initiate STK push to customer's phone
        """
        amount = request.data.get('amount')
        phone = request.data.get('phone')
        user_id = request.user
        subscription_type = request.data.get('subscription_type', 'monthly')

        if not amount or not phone:
            return Response(
                {"message": "Amount, phone number and user ID are required",
                 "data":[]
                 },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        phone = self.format_phone_number(phone)

        access_token = MpesaAccessToken.validated_mpesa_access_token
        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": "Bearer %s" % access_token}
        request_data = {
            "BusinessShortCode": LipanaMpesaPassword.Business_short_code,
            "Password": LipanaMpesaPassword.decode_password,
            "Timestamp": LipanaMpesaPassword.lipa_time,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": LipanaMpesaPassword.Business_short_code,
            "PhoneNumber": phone,
            "CallBackURL":MpesaC2bCredential.callback_url,
            "AccountReference": "Mercy Saline",
            "TransactionDesc": "Site Report Charges"
        }

        response = requests.post(api_url, json=request_data, headers=headers)
        response_data = response.json()
        
        if response.status_code == 200:
            checkout_request_id = response_data.get('CheckoutRequestID')
            customer_message = response_data.get('CustomerMessage')

            transaction = Transactions.objects.create(
                student=user_id,
                phone_number=phone,
                amount=amount,
                subscription_type=subscription_type,
                result_description= customer_message,
                checkout_id=checkout_request_id,
                status='pending'
            )

            return Response({
                "success": True,
                "message": customer_message,
                "data": response_data,
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "message": 'Failed to initiate payment'
            }, status=response.status_code)
        
@csrf_exempt
def callback(request):
    if request.method != 'POST':
        return Response({"error": "Method not allowed"}, status=405)
    else:
        try:
            # Handling text/plain content type
            content_type = request.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                # If content type is not JSON, assume it's text/plain and parse it as JSON
                callback_data = json.loads(request.body.decode('utf-8'))
            else:
                # If content type is JSON, parse it directly
                callback_data = json.loads(request.body.decode('utf-8'))
            print(callback_data)
            print('this is the callback data')

            result_code = callback_data["Body"]["stkCallback"]["ResultCode"]
            checkout_id = callback_data["Body"]["stkCallback"]["CheckoutRequestID"]

            print(result_code, checkout_id)
            if result_code != 0:
                # Updating transaction as failed if it fails
                result_description = callback_data["Body"]["stkCallback"]["ResultDesc"]
                Transactions.objects.filter(checkout_id=checkout_id).update(status="failed", result_description=result_description,)
                return Response({"result_code": result_code})

            result_description = callback_data["Body"]["stkCallback"]["ResultDesc"]
            body = callback_data["Body"]["stkCallback"]["CallbackMetadata"]["Item"]
            mpesa_code = next(item["Value"] for item in body if item["Name"] == "MpesaReceiptNumber")
            phone_number = next(item["Value"] for item in body if item["Name"] == "PhoneNumber")
            amount = next(item["Value"] for item in body if item["Name"] == "Amount")
            

            Transactions.objects.filter(checkout_id=checkout_id).update(
                amount=amount,
                mpesa_code=mpesa_code,
                phone_number=phone_number,
                status="completed",
                result_description=result_description
            )
            print("process ended")

            return Response({"status": "success", "mpesa_code": mpesa_code})

        except (json.JSONDecodeError, KeyError) as e:
            return Response(f"Invalid Request: {str(e)}")

class PaymentStatusAPIView(APIView):
    permission_classes=[IsAuthenticated]
    """
    To retrive all the transactions made by a user
    """
    schema = AutoSchema()
    def get(self, request, *args, **kwargs):
        transactions=Transactions.objects.filter(student=request.user)
        serializer=TransactionsSerializer(transactions, many=True)        
        return Response(
            {
                "message":"Transaction retrieved sucessfully",
                "data":serializer.data
            },
            status=status.HTTP_200_OK
        )
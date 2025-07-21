from rest_framework.views import APIView
from rest_framework.response import Response

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from payment_app.serializers import TransactionsSerializer

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

import requests
from datetime import datetime
import base64
from django.conf import settings
import json
from .models import Transactions
from django.contrib.auth import get_user_model
from rest_framework.schemas import AutoSchema

from django_daraja.mpesa.core import MpesaClient
User = get_user_model()

cl = MpesaClient()

@method_decorator(csrf_exempt, name='dispatch')
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

        print("Incoming Data:", request.data)


        phone_number = request.data.get('phone')

        if not phone_number:
            return Response({"message": "Phone number is required."}, status=status.HTTP_400_BAD_REQUEST)

        phone_number = self.format_phone_number(phone_number)
        amount = request.data.get('amount')
        try:
            amount = int(float(amount))
        except (ValueError, TypeError):
            return Response({"message": "Invalid amount provided."}, status=status.HTTP_400_BAD_REQUEST)
        account_reference = 'Subsription'
        transaction_desc = 'Payment for subscription'

        user=request.user
        student_name = f"{user.first_name} {user.last_name}"
        student_email=user.email
    
        subscription_type = request.data.get('subscription_type', 'monthly')
        callback_url = 'https://lughanest-backend-apis.onrender.com/api/v1/payment/callback/'
        response = cl.stk_push(
            phone_number, 
            amount, 
            account_reference, 
            transaction_desc, 
            callback_url
            )

        response_data = response.json()
        
        if response.status_code == 200:
            checkout_request_id = response_data.get('CheckoutRequestID')
            customer_message = response_data.get('CustomerMessage')

            Transactions.objects.create(
                student=request.user,
                student_name=student_name,
                student_email=student_email,
                phone_number=phone_number,
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
    
        
@method_decorator(csrf_exempt, name='dispatch')
class MpesaCallbackAPIView(APIView):
    def post(self, request):
        try:
            raw_data = request.body.decode('utf-8')
            
            callback_data = json.loads(raw_data)
            print(callback_data)

            result_code = callback_data["Body"]["stkCallback"]["ResultCode"]
            checkout_id = callback_data["Body"]["stkCallback"]["CheckoutRequestID"]

            if result_code != 0:
                result_description = callback_data["Body"]["stkCallback"]["ResultDesc"]

                transactions = Transactions.objects.filter(checkout_id=checkout_id)

                for transaction in transactions:
                    transaction.status = "failed"
                    transaction.result_description = result_description
                    transaction.save()

                return Response({
                    "status": "failed",
                    "message": "Payment Failed"
                }, status=status.HTTP_200_OK)

            result_description = callback_data["Body"]["stkCallback"]["ResultDesc"]
            body = callback_data["Body"]["stkCallback"]["CallbackMetadata"]["Item"]
            mpesa_code = next(item["Value"] for item in body if item["Name"] == "MpesaReceiptNumber")
            phone_number = next(item["Value"] for item in body if item["Name"] == "PhoneNumber")
            amount = next(item["Value"] for item in body if item["Name"] == "Amount")

            transactions = Transactions.objects.filter(checkout_id=checkout_id)

            for transaction in transactions:
                transaction.amount = amount
                transaction.mpesa_code = mpesa_code
                transaction.phone_number = phone_number
                transaction.status = "completed"
                transaction.result_description = result_description
                transaction.save() 

            print("process ended")

            return Response({
                "status": "success",
                "message": "Payment successful"
            }, status=status.HTTP_200_OK)

        except (json.JSONDecodeError, KeyError) as e:
            return Response(
                {"error": f"Invalid Request: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class PaymentDataAPIView(APIView):
    permission_classes=[IsAuthenticated]
    """
    To retrive all the transactions made by a user
    """
    schema = AutoSchema()
    def get(self, request, *args, **kwargs):
        transactions=Transactions.objects.filter(student=request.user).order_by('-payment_date')
        serializer=TransactionsSerializer(transactions, many=True)        
        return Response(
            {
                "message":"Transaction retrieved sucessfully",
                "data":serializer.data
            },
            status=status.HTTP_200_OK
        )


class PaymentProcessingAPIView(APIView):
    def get(self, request, *args, **kwargs):
        phone = request.query_params.get('phone')

        if not phone:
            return Response({"success": False, "message": "Phone number is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Transactions.objects.filter(phone_number=phone).latest('payment_date')
            return Response({
                "success": True,
                "status": payment.status,
                "message": f"Payment status is {payment.status}"
            })
        except Transactions.DoesNotExist:
            return Response({"success": False, "status": "Pending", "message": "No payment found."})
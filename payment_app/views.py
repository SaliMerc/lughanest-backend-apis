from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
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
    def post(self, request, *args, **kwargs):
        """
        Initiate STK push to customer's phone
        """
        amount = request.data.get('amount')
        phone = request.data.get('phone')
        user_id = request.user
        subscription_type = request.data.get('subscription_type', 'monthly')

        print(amount, phone, user_id.first_name)

        if not amount or not phone:
            return Response(
                {"message": "Amount, phone number and user ID are required",
                 "data":[]
                 },
                status=status.HTTP_400_BAD_REQUEST
            )

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
            # this should be a public url maybe from the hosted site or ngrok
            "CallBackURL":MpesaC2bCredential.callback_url,
            "AccountReference": "Mercy Saline",
            "TransactionDesc": "Site Report Charges"
        }

        response = requests.post(api_url, json=request_data, headers=headers)
        response_data = response.json()

        if response.status_code == 200:
            # Create a new transaction record
            checkout_request_id = response_data.get('CheckoutRequestID')
            merchant_request_id = response_data.get('MerchantRequestID')
            customer_message = response_data.get('CustomerMessage')

            transaction = Transactions.objects.create(
                student=user_id,
                phone_number=phone,
                amount=amount,
                subscription_type=subscription_type,
                checkout_id=checkout_request_id,
                status='pending'
            )

            return Response({
                "success": True,
                "message": customer_message,
                "data": response_data,
                "transaction_id": transaction.id
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "error": response_data.get('errorMessage', 'Failed to initiate payment')
            }, status=response.status_code)

    # except User.DoesNotExist:
    #     return Response(
    #         {"error": "User not found"},
    #         status=status.HTTP_404_NOT_FOUND
    #     )
    # except Exception as e:
    #     return Response(
    #         {"error": "An error occurred while processing your request"},
    #         status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #     )

def format_phone_number(self, phone):
    """Format phone number to 2547XXXXXXXX"""
    if phone.startswith('0'):
        return '254' + phone[1:]
    elif phone.startswith('+254'):
        return phone[1:]
    return phone


class MpesaCallbackAPIView(APIView):
    """
    Handle M-Pesa callback after payment is completed
    """
    schema = AutoSchema()
    
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            
            # Safely get nested dictionary values
            callback_metadata = data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {})
            items = callback_metadata.get('Item', [])
            
            payment_data = {
                'merchant_request_id': data.get('Body', {}).get('stkCallback', {}).get('MerchantRequestID', ''),
                'checkout_request_id': data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID', ''),
                'result_code': data.get('Body', {}).get('stkCallback', {}).get('ResultCode', ''),
                'result_desc': data.get('Body', {}).get('stkCallback', {}).get('ResultDesc', ''),
                'amount': None,
                'mpesa_receipt_number': None,
                'transaction_date': None,
                'phone_number': None,
            }

            # Extract values from callback metadata
            for item in items:
                if item.get('Name') == 'Amount':
                    payment_data['amount'] = item.get('Value')
                elif item.get('Name') == 'MpesaReceiptNumber':
                    payment_data['mpesa_receipt_number'] = item.get('Value')
                elif item.get('Name') == 'TransactionDate':
                    payment_data['transaction_date'] = item.get('Value')
                elif item.get('Name') == 'PhoneNumber':
                    payment_data['phone_number'] = item.get('Value')

            # Update the transaction record
            try:
                transaction = Transactions.objects.get(
                    checkout_id=payment_data['checkout_request_id']
                )
                
                transaction.mpesa_code = payment_data['mpesa_receipt_number']
                transaction.status = 'completed' if payment_data['result_code'] == 0 else 'failed'
                transaction.result_description = payment_data['result_desc']
                transaction.save()
                
                # The signal will handle the subscription dates and is_active status
                
            except Transactions.DoesNotExist:
                return None
            # M-Pesa expects a response
            response = {
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
            return Response(response, status=status.HTTP_200_OK)

        except Exception as e:
            response = {
                "ResultCode": 1,
                "ResultDesc": "Rejected"
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class PaymentStatusAPIView(APIView):
    """
    Check payment status by checkout_request_id or transaction ID
    """
    schema = AutoSchema()
    def get(self, request, *args, **kwargs):
        checkout_id = request.query_params.get('checkout_id')
        transaction_id = request.query_params.get('transaction_id')
        
        if not checkout_id and not transaction_id:
            return Response(
                {"error": "Either checkout_id or transaction_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if checkout_id:
                transaction = Transactions.objects.get(checkout_id=checkout_id)
            else:
                transaction = Transactions.objects.get(id=transaction_id)
                
            data = {
                'id': transaction.id,
                'student': transaction.student.id,
                'student_name': transaction.student.get_full_name(),
                'status': transaction.status,
                'amount': str(transaction.amount),
                'phone_number': transaction.phone_number,
                'subscription_type': transaction.subscription_type,
                'mpesa_code': transaction.mpesa_code,
                'is_active': transaction.is_active,
                'subscription_start_date': transaction.subscription_start_date,
                'subscription_end_date': transaction.subscription_end_date,
                'result_description': transaction.result_description,
                'created_at': transaction.created_at
            }
            return Response(data, status=status.HTTP_200_OK)
            
        except Transactions.DoesNotExist:
            return Response(
                {"error": "Transaction not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
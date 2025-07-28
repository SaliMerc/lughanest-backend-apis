from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from payment_app.serializers import *
from payment_app.models import *

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from django.contrib.auth import get_user_model
from rest_framework.schemas import AutoSchema

from django_daraja.mpesa.core import MpesaClient
from django.conf import settings
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
        phone_number = request.data.get('phone')

        if not phone_number:
            return Response({"message": "Phone number is required."}, status=status.HTTP_400_BAD_REQUEST)

        phone_number = self.format_phone_number(phone_number)
        amount = request.data.get('amount')
        subscription_type = request.data.get('subscription_type')
        try:
            amount = int(float(amount))
        except (ValueError, TypeError):
            return Response({"message": "Invalid amount provided."}, status=status.HTTP_400_BAD_REQUEST)
        account_reference = 'LughaNest'
        transaction_desc = f'Subscription for plan {subscription_type} plan'

        user=request.user
        student_name = f"{user.first_name} {user.last_name}"
        student_email=user.email
    
        callback_url = settings.CALLBACK_URL    
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
                student_id=request.user,
                student_name=student_name,
                student_email=student_email,
                phone_number=phone_number,
                amount=amount,
                transaction_subscription_type=subscription_type,
                payment_type='MPESA',
                transaction_result_description= customer_message,
                transaction_reference_number=checkout_request_id,
                transaction_status='pending'
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
   
            result_code = callback_data["Body"]["stkCallback"]["ResultCode"]
            checkout_id = callback_data["Body"]["stkCallback"]["CheckoutRequestID"]

            if result_code != 0:
                result_description = callback_data["Body"]["stkCallback"]["ResultDesc"]

                transactions = Transactions.objects.filter(transaction_reference_number=checkout_id)

                for transaction in transactions:
                    transaction.transaction_status = "failed"
                    transaction.transaction_result_description = result_description
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

            transactions = Transactions.objects.filter(transaction_reference_number=checkout_id)

            for transaction in transactions:
                transaction.amount = amount
                transaction.transaction_code = mpesa_code
                transaction.phone_number = phone_number
                transaction.transaction_status = "completed"
                transaction.transaction_result_description = result_description
                transaction.save() 

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
        subscriptions=Subscriptions.objects.filter(student_id=request.user).select_related('student_id', 'transaction_id').order_by('-subscription_date')

        serializer=SubscriptionsSerializer(subscriptions, many=True)        
        return Response(
            {
                "result_code":0,
                "message":"Transaction retrieved sucessfully",
                "data":serializer.data
            },
            status=status.HTTP_200_OK
        )


class PaymentProcessingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    """
    To check if the payment made by a user has gone through
    """
    def get(self, request, *args, **kwargs):
        try:
            payment = Transactions.objects.filter(student_id=request.user).select_related('student_id').order_by('-transaction_date').first()

            now = timezone.now()
            active_subscriptions = Subscriptions.objects.filter(
                student_id=request.user,
                transaction_id__transaction_status='completed',  
                subscription_start_date__lte=now,
                subscription_end_date__gte=now 
            )
            
            """Check if user has any active subscription"""
            has_active_subscription = active_subscriptions.exists()

            if has_active_subscription:
                has_active_subscription ==True
            else:
                has_active_subscription ==False
            
            """Get subscription details (we'll take the first active one if multiple exist)"""
            if has_active_subscription:
                subscription = active_subscriptions.first()
                active_plan = {
                    "subscription_type": subscription.subscription_type,
                    "start_date": subscription.subscription_start_date,
                    "end_date": subscription.subscription_end_date
                }
            else:
                active_plan={
                    "subscription_type": 'None',
                    "start_date": 'None',
                    "end_date": 'None'
                }  
            return Response({
            "success": True,
            "status": payment.transaction_status,
            "amount": payment.amount,
            "has_active_subscription": has_active_subscription,
            "active_plan": active_plan
        })  

        except Transactions.DoesNotExist:
            return Response({
                "success": False,
                "status": "pending",
                "message": "No payment found for this user.",
                "active_plan": active_plan
            })
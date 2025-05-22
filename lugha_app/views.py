import random
import datetime
from urllib import request

from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from LughaNestBackend import settings
from lugha_app.models import *
from .serializers import *

"""All functions to do with signup, login, verification, password  reset, and viewing user details"""
class UserViewSet(viewsets.ModelViewSet):
    queryset=MyUser.objects.all()
    serializer_class=UserSerializer

    """Users can signup and login easily but have to be logged in to update their details"""
    def get_permissions(self):
        if self.action in ['create','login','verify_otp','resend_otp']:
            return [AllowAny()]
        return [IsAuthenticated()]

    """For signup"""
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        user.otp=str(random.randint(100000,999999))
        user.otp_expiry=timezone.now() + datetime.timedelta(minutes=15)
        user.save()

        """Sending an email with the otp"""
        send_mail(
            subject='LughaNest Account Verification',
            message=f" Hello {user.first_name}, \n \n \n Your OTP is {user.otp} \n Enter the OTP to proceed with you account creation \n \n \n \n LughaNest Team",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email]
        )

        return Response({"detail":"OTP sent, check your email to activate your account"},status=status.HTTP_201_CREATED)

    """For OTP Verification"""
    @action(detail=False, methods=['POST'], permission_classes=[AllowAny], url_path='otp-verification')
    def verify_otp(self, request):
        email=request.data.get("email")
        otp=request.data.get("otp")

        try:
            user = MyUser.objects.get(email=email)

            if user.is_active:
                return Response({"detail":"Your account has already been verified"},status=status.HTTP_200_OK)

            if otp != user.otp:
                return Response({"detail":"The OTP is invalid"},status=status.HTTP_400_BAD_REQUEST)

            if user.otp_expiry and timezone.now() > user.otp_expiry:
                return Response({"detail":"OTP expired, request a new one"},status=status.HTTP_400_BAD_REQUEST)

            user.is_active=True
            user.otp=None
            user.otp_expiry=None
            user.save()

            send_mail(
                subject='Welcome to LughaNest',
                message=f"Hello {user.first_name}, \n \n \nYour account has successfully been verified \nYou can now log in and interact with our courses and enjoy personalised dashboard with your learning metrics.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True
            )

            return Response({"success":"Your account was verified successfully"},status=status.HTTP_200_OK)
        except MyUser.DoesNotExist:
            return Response({"detail":"Email not found"},status=status.HTTP_400_BAD_REQUEST)

    """For Resending OTP"""
    @action(detail=False, methods=['POST'], permission_classes=[AllowAny], url_path='resend-otp')
    def resend_otp(self, request):
        email=request.data.get("email")

        try:
            user = MyUser.objects.get(email=email)

            if user.is_active:
                return Response({"detail":"Your account has already been verified"},status=status.HTTP_200_OK)

            user.otp = str(random.randint(100000, 999999))
            user.otp_expiry = timezone.now() + datetime.timedelta(minutes=15)
            user.save()

            send_mail(
                subject='New OTP',
                message=f" Hello {user.first_name}, \n \n \n Your new OTP is {user.otp} \n Enter the OTP to complete you account creation \n \n \n \n LughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email]
            )

            return Response({"detail": "OTP sent, check your email to activate your account"}, status=status.HTTP_201_CREATED)

        except MyUser.DoesNotExist:
            return Response({"detail":"Email not found"},status=status.HTTP_400_BAD_REQUEST)

    """ToDo: Add the Password reset function"""

    """For login"""
    @action(detail=False, methods=['POST'], permission_classes=[AllowAny], url_path='login')
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Logged in successfully",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data
            })
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    """For password change when the users are logged in"""
    @action(detail=False, methods=['POST'],url_path='change-password')
    def change_password(self, request):
        user = request.user
        old_password = request.data.get("old-password")
        new_password = request.data.get("new-password")
        confirm_password = request.data.get("confirm-password")

        if not old_password or not new_password:
            return Response({"error": "Both old and new passwords are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"error": " New passwords need to be the same."}, status=status.HTTP_400_BAD_REQUEST)

        if new_password == old_password:
            return Response({"error": " New password cannot be the same as the old password"}, status=status.HTTP_200_OK)

        user.set_password(new_password)
        user.save()

        send_mail(
            subject='Password update',
            message=f" Hello {user.first_name}, \n \n \n Your password was changed \n If you did not perform this action, kindly let us know. \n \n \n \n LughaNest Team",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email]
        )

        return Response({"message": "Password updated successfully."}, status=200)

    """For the users to view all their profile details"""
    @action(detail=False, methods=['GET'], url_path='profile-details')
    def profile_details(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)

    """For updating both the profile details and the profile picture (separately per the design)"""
    @action(detail=False, methods=['PATCH'], url_path='update-profile-details')
    def update_profile(self, request):
        user = request.user
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully", "user": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
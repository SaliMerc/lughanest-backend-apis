import random
import datetime
from urllib import request

from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth.handlers.modwsgi import check_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import HttpResponse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
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
class UserViewSet(viewsets.ViewSet):
    queryset=MyUser.objects.all()
    serializer_class=UserSerializer

    """Users can signup and login easily but have to be logged in to update their details"""
    def get_permissions(self):
        if self.action in ['create','login','verify_otp','resend_otp', 'password_reset_not_logged_in','password_reset_not_logged_in_confirmation']:
            return [AllowAny()]
        return [IsAuthenticated()]

    """For signup"""
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
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
    @action(detail=False, methods=['POST'], url_path='otp-verification')
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
            user.verified_at=timezone.now()
            user.otp=None
            user.otp_expiry=None
            user.save()

            send_mail(
                subject='Welcome to LughaNest',
                message=f"Hello {user.first_name}, \n \n \nYour account has successfully been verified \nYou can now log in and interact with our courses and enjoy personalised dashboard with your learning metrics. \n \n \n \n LughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True
            )

            return Response({"success":"Your account was verified successfully"},status=status.HTTP_200_OK)
        except MyUser.DoesNotExist:
            return Response({"detail":"Email not found"},status=status.HTTP_400_BAD_REQUEST)

    """For Resending OTP"""
    @action(detail=False, methods=['POST'],url_path='resend-otp')
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

    """Password reset function (When not logged in"""
    @action(detail=False, methods=['POST'], url_path='password-reset-not-logged-in')
    def password_reset_not_logged_in(self, request):
        email=request.data.get("email")

        try:
            user=MyUser.objects.get(email=email)

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.id))

            user.otp = str(random.randint(100000, 999999))
            user.otp_expiry = timezone.now() + datetime.timedelta(minutes=15)
            user.save()

            reset_link = f"{request.scheme}://{request.get_host()}/reset/{uid}/{token}/"

            send_mail(
                subject='Password Reset Link',
                message=f" Hello {user.first_name}, \n \n \n Here is your password reset link and an OTP that you will use to recover your account \n Your OTP is {user.otp}\n\n Click the link below  to continue with your password reset\n {reset_link} \n \n \n \n LughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email]
            )
            return Response({"message":"A password reset email has been sent to your account, follow the link to continue with your password recovery"},status=status.HTTP_200_OK)
        except MyUser.DoesNotExist:
            return Response({"message":"A user with this email does not exist"},status=status.HTTP_400_BAD_REQUEST)

    """Password reset function (When not logged in"""

    @action(detail=False, methods=['POST'], url_path='password-reset-not-logged-in-confirmation')
    def password_reset_not_logged_in_confirmation(self, request):
        uidb64=request.data.get('uidb64')
        token=request.data.get('token')
        otp = request.data.get('otp')

        if not uidb64 or not token:
            return Response({"message":"Both token and uuidb are required"},status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                uid = force_str(urlsafe_base64_decode(uidb64))
                user = MyUser.objects.get(id=uid)
            except (TypeError, ValueError, OverflowError, MyUser.DoesNotExist):
                return Response({"message":"Invalid uidb64 or token"},status=status.HTTP_400_BAD_REQUEST)

        if not user or not default_token_generator.check_token(user, token):
            return Response({"message":"Invalid token or user does not exist"},status=status.HTTP_400_BAD_REQUEST)

        if user.otp !=otp or (user.otp_expiry and timezone.now() > user.otp_expiry):
            return Response({"message":"Invalid or expired OTP"},status=status.HTTP_400_BAD_REQUEST)

        try:
            new_password=request.data.get('new-password')
            confirm_password = request.data.get('confirm-password')

            if not new_password or not confirm_password:
                return Response({"message":"Both passwords should be provided"},status=status.HTTP_400_BAD_REQUEST)

            if new_password != confirm_password:
                return Response({"message":"New password and confirm password should be the same."}, status=status.HTTP_400_BAD_REQUEST)

            if user.check_password(new_password):
                return Response({"message":"The new password cannot be the same as the old password."}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.otp=None
            user.otp_expiry=None
            user.save()

            send_mail(
                subject='Password Reset',
                message=f" Hello {user.first_name}, \n \n \n Your Password was reset successfully. If you did not perform this action, kindly let us know. \n \n \n \n LughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email]
            )

            return Response({"message":"Your password has been changed successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"message":"Invalid data"},status=status.HTTP_400_BAD_REQUEST)

    """For login"""
    @action(detail=False, methods=['POST'],url_path='login')
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

        """Updating the session so that the user remains logged in (Has both JWT and session auth for when JWT is not working"""
        if hasattr(request, 'session'):
            update_session_auth_hash(request, user)

        if 'rest_framework_simplejwt' in settings.INSTALLED_APPS:
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Password updated successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            })

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
        """Retrieve the old email in case the user changes it during profile update"""
        old_email=user.email
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_email = serializer.validated_data.get('email')

        if new_email and new_email!= old_email:
            if MyUser.objects.filter(email=new_email).exists():
                return Response({"message": "A user with this email already exists, please choose a new email."}, status=status.HTTP_400_BAD_REQUEST)
            user.otp = str(random.randint(100000, 999999))
            user.otp_expiry = timezone.now() + datetime.timedelta(minutes=15)
            user.updated_email = new_email
            user.save()

            """Notifying the account owner that they have requested an email change"""
            send_mail(
                subject='Profile update',
                message=f" Hello {user.first_name}, \n \n \n We have received a request to change you email from {old_email} to {new_email}\n If you did not make this request, please let us know.\n \n \n \n LughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email]
            )
            """Email containing the code"""
            send_mail(
                subject='Updated Email Verification',
                message=f" Hello {user.first_name}, \n \n \n Your OTP is {user.otp} \n Enter the OTP to proceed with your profile update \n \n \n \n LughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[new_email]
            )

            return Response({"detail": "Email verification sent."}, status=status.HTTP_200_OK)
        serializer.save()
        return Response({"detail":"Profile updated successfully","user":serializer.data}, status=status.HTTP_200_OK)

    """Profile update OTP Verification (if email is changed)"""
    @action(detail=False, methods=['POST'],url_path='new-email-otp-verification')
    def verify_email_otp(self, request):
        """Get the current email of the user"""
        email=request.data.get("email")
        otp=request.data.get("otp")

        try:
            user = MyUser.objects.get(email=email)

            if otp != user.otp:
                return Response({"detail":"The OTP is invalid"},status=status.HTTP_400_BAD_REQUEST)

            if user.otp_expiry and timezone.now() > user.otp_expiry:
                return Response({"detail":"OTP expired, request a new one"},status=status.HTTP_400_BAD_REQUEST)

            send_mail(
                subject='Verification Successful',
                message=f"Hello {user.first_name}, \n \n \nYour new email has been verified successfully. \n \n \n \n LughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.updated_email],
                fail_silently=True
            )

            user.email = user.updated_email
            user.updated_email = None
            user.otp = None
            user.otp_expiry = None
            user.save()

            return Response({"success":"Your account was verified successfully"},status=status.HTTP_200_OK)
        except MyUser.DoesNotExist:
            return Response({"detail":"Your Email account has changed. To revert to your old email, update your email address."},status=status.HTTP_400_BAD_REQUEST)

class BlogViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    def get_queryset(self):
        return Blog.objects.all()

    def get_serializer(self, *args, **kwargs):
        return BlogSerializer(*args, **kwargs)

    @action(detail=False, methods=['GET'], url_path='all-blog-items')
    def all_blog_items(self, request):
        blogs=self.get_queryset()
        serializer = self.get_serializer(blogs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'], url_path='blog-detail')
    def blog_detail(self, request, pk=None):
        try:
            blog = self.get_queryset().get(pk=pk)
            serializer = self.get_serializer(blog)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Blog.DoesNotExist:
            return Response({"message":"Blog does not exist."})

class LegalItemsViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def get_queryset(self):
        return LegalItem.objects.all()

    def get_serializer(self, *args, **kwargs):
        return LegalItemsSerializer(*args, **kwargs)

    @action(detail=False, methods=['GET'], url_path='legal-items')
    def legal_items(self, request):
        legal_items = self.get_queryset().first()
        serializer = self.get_serializer(legal_items)
        return Response(serializer.data, status=status.HTTP_200_OK)






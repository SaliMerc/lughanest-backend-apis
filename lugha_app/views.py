import random
import datetime
from logging import raiseExceptions
from urllib import request
from django.db.models import Min, Prefetch
from django.shortcuts import redirect, get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser

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
from rest_framework_simplejwt.tokens import RefreshToken,TokenError

from django.db import transaction

import jwt


from LughaNestBackend import settings
from lugha_app.models import *
from .serializers import *

from rest_framework.views import APIView
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings

from collections import defaultdict

class GoogleAuthView(APIView):
    def post(self, request):
        token = request.data.get('token')
        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
            email = idinfo['email']
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            profile_picture=idinfo.get('picture','')
            user, created = MyUser.objects.get_or_create(email=email,
                                                   defaults={'username': email, 'first_name': first_name,
                                                             'last_name': last_name, 'display_name':email,'profile_picture':profile_picture,'accepted_terms_and_conditions':True}
                                                   )
            if not created:
                user.last_login = datetime.datetime.now()
                user.save()
            user.save()
            if created:
                send_mail(
                    subject='Welcome to LughaNest',
                    message=f"Hello {user.first_name}, \n \n \nYour account has been created successfully \nYou can now interact with our courses and enjoy personalised dashboard with your learning metrics. \n \n \n \n LughaNest Team",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=True
                )
            serializer= UserSerializer(user, context={'request': request})
            refresh = RefreshToken.for_user(user)
            response= Response({
                'status':"Authentication successful.",
                "user":serializer.data,
                "access_token": str(refresh.access_token),
                "refresh": str(refresh)
            })
            # response.set_cookie(
            #     settings.SIMPLE_JWT['AUTH_COOKIE'],
            #     str(refresh.access_token),
            #     max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
            #     secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            #     httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            #     samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            # )
            #
            # response.set_cookie(
            #     settings.SIMPLE_JWT['REFRESH_COOKIE'],
            #     str(refresh),
            #     max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
            #     secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            #     httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            #     samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            # )

            return response
        except Exception as e:
            return Response({'error': f'Invalid token\n {e}'}, status=400)


"""All functions to do with signup, login, verification, password  reset, and viewing user details"""
class UserViewSet(viewsets.ViewSet):
    queryset=MyUser.objects.all()
    serializer_class=UserSerializer

    """Users can signup and login easily but have to be logged in to update their details"""
    def get_permissions(self):
        if self.action in ['create','login','verify_account','resend_verification', 'password_reset_not_logged_in','password_reset_not_logged_in_confirmation','validate_token','confirm_reset']:
            return [AllowAny()]
        return [IsAuthenticated()]

    """For signup"""
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        try:
            verify_token = jwt.encode({
                    "user_id": user.id,
                    "exp": datetime.datetime.now() + timedelta(hours=24),
                    "type": "verify_account"
                },
                settings.SECRET_KEY,
                algorithm="HS256"
            )

            activation_link=f"{settings.FRONTEND_HOST}/account-verification?t={verify_token}"

            send_mail(
                subject='LughaNest Account Verification',
                message=f"Hello {user.first_name},\n\nHere is your account activation link:\n\n{activation_link}, follow thee link to verify and activate your account.\n\nLughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return Response(
                {"message": "Activation link has been sent to your email address"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            print(e)
            return Response(
                {"message": "Account created but failed to send activation email"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    """For Email Verification and account activation"""
    @action(detail=False, methods=['POST'], url_path='account-verification')
    def verify_account(self, request):
        reset_jwt = request.data.get('jwt')

        try:
            payload = jwt.decode(
                reset_jwt,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"require": ["exp", "user_id", "type"]}
            )
            if payload.get("type") != "verify_account":
                raise jwt.InvalidTokenError
            if datetime.datetime.now() > datetime.datetime.fromtimestamp(payload['exp']):
                return Response({"message": "The token has expired. Request a new one."})

            user = MyUser.objects.get(id=payload["user_id"])

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, MyUser.DoesNotExist) as e:
            return Response(
                {"error": "Invalid or expired token", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if user.is_active:
                return Response({"message":"Your account has already been verified."})
            user.is_active=True
            user.verified_at=datetime.datetime.now()
            user.save()

            send_mail(
                subject='Welcome to LughaNest',
                message=f"Hello {user.first_name}, \n \n \nYour account has successfully been verified \nYou can now log in and interact with our courses and enjoy personalised dashboard with your learning metrics. \n \n \n \n LughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True
            )

            return Response({"message":"Your account was verified successfully"},status=status.HTTP_200_OK)
        except MyUser.DoesNotExist:
            return Response({"message":"Email not found"},status=status.HTTP_400_BAD_REQUEST)

    """For Resending verification email"""
    @action(detail=False, methods=['POST'],url_path='resend-verification')
    def resend_verification(self, request):
        email=request.data.get("email")

        try:
            user=MyUser.objects.get(email=email)


            if user.is_active:
                return Response({"message":"You account has already been verified. Login to continue"})



            verify_token = jwt.encode({
                "user_id": user.id,
                "exp": datetime.datetime.now() + timedelta(hours=24),
                "type": "verify_account"
            },
                settings.SECRET_KEY,
                algorithm="HS256"
            )

            activation_link = f"{settings.FRONTEND_HOST}/account-verification?t={verify_token}"

            send_mail(
                subject='LughaNest Account Verification',
                message=f"Hello {user.first_name},\n\nHere is your account activation link:\n\n{activation_link}, follow thee link to verify and activate your account.\n\nLughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return Response(
                {"message": "Activation link has been sent to your email address"},
                status=status.HTTP_200_OK
            )

        except MyUser.DoesNotExist:
            return Response(
                {"message": "A user with this email address does not exist."},
                status=status.HTTP_200_OK
            )


    """Password reset function (When not logged in)"""
    @action(detail=False, methods=['POST'], url_path='password-reset-not-logged-in')
    def password_reset_not_logged_in(self, request):
        email=request.data.get("email")

        try:
            user=MyUser.objects.get(email=email)

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.id))
            reset_link = f"{request.scheme}:/{settings.FRONTEND_HOST}/change-password?u={uid}&t={token}"

            send_mail(
                subject='Password Reset Link',
                message=f" Hello {user.first_name}, \n \n \n Here is your one time password reset link that you will use to recover your account \n\n\n Click the link below  to continue with your password reset\n {reset_link} \n \n \n \n LughaNest Team",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email]
            )
            return Response({"message":"A password reset link has been sent to your email account, follow the link to continue."},status=status.HTTP_200_OK)
        except MyUser.DoesNotExist:
            return Response({"message":"A user with this email does not exist"},status=status.HTTP_400_BAD_REQUEST)

    """Password reset function (When not logged in"""
    @action(detail=False, methods=['post'], url_path='validate-reset-token')
    def validate_token(self, request):
        """Validating the token in the email link"""
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = MyUser.objects.get(id=uid)
        except (TypeError, ValueError, OverflowError, MyUser.DoesNotExist):
            return Response(
                {"valid": False, "error": "Invalid user"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"valid": False, "error": "Invalid token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        reset_jwt = jwt.encode(
            {
                "user": user.id,
                "exp": datetime.datetime.now() + timedelta(minutes=5),
                "type": "password_reset"
            },
            settings.SECRET_KEY,
            algorithm="HS256"
        )

        return Response({
            "valid": True,
            "jwt": reset_jwt,
            "expires_in": "5 minutes"
        })

    @action(detail=False, methods=['post'], url_path='confirm-password-reset')
    def confirm_reset(self, request):
        """The jwt token will then be used to identify the user while they are resetting their password"""
        reset_jwt = request.data.get('jwt')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        try:
            payload = jwt.decode(
                reset_jwt,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"require": ["exp", "user", "type"]}
            )

            if payload.get("type") != "password_reset":
                raise jwt.InvalidTokenError
            if datetime.datetime.now() > datetime.datetime.fromtimestamp(payload['exp']):
                return Response({"message":"The token has expired. Request a new one."})

            user = MyUser.objects.get(id=payload["user"])

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, MyUser.DoesNotExist) as e:
            return Response(
                {"error": "Invalid or expired token", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            if len(new_password) < 8:
                return Response(
                    {"message": "Password must be at least 8 characters"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not new_password or not confirm_password:
                return Response({"message":"Both passwords should be provided"},status=status.HTTP_400_BAD_REQUEST)

            if new_password != confirm_password:
                return Response({"message":"New password and confirm password should be the same."}, status=status.HTTP_400_BAD_REQUEST)

            if user.check_password(new_password):
                return Response({"message":"The new password cannot be the same as the old password."}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()
        except Exception as e:
            return Response({"message":"An error was encountered while performing this action"})

        send_mail(
            subject='Password Reset',
            message=f" Hello {user.first_name}, \n \n \n Your Password was reset successfully. If you did not perform this action, kindly let us know. \n \n \n \n LughaNest Team",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email]
        )

        user.set_password(new_password)
        user.save()

        return Response({
            "success": True,
            "message": "Password updated successfully"
        })

    """For login"""
    @action(detail=False, methods=['POST'],url_path='login')
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            this_user=MyUser.objects.get(username=username)
            if not this_user.check_password(password):
                return Response({"message": "The password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        except MyUser.DoesNotExist:
            return Response({"message":"A user with this email does not exist."})
        user = authenticate(username=username, password=password)
        serializer=UserSerializer(user,context={'request': request})
        if user:
            refresh = RefreshToken.for_user(user)
            response= Response({
                "message": "Logged in successfully",
                "user": serializer.data,
                "access_token":str(refresh.access_token),
                "refresh": str(refresh)
            })

            # response.set_cookie(
            #     settings.SIMPLE_JWT['AUTH_COOKIE'],
            #     str(refresh.access_token),
            #     max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
            #     secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            #     httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            #     samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            # )
            #
            # response.set_cookie(
            #     settings.SIMPLE_JWT['REFRESH_COOKIE'],
            #     str(refresh),
            #     max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
            #     secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            #     httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            #     samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            # )

            return response
        return Response({"message": "Wrong credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    """For password change when the users are logged in"""
    @action(detail=False, methods=['POST'],url_path='change-password')
    def change_password(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not old_password or not new_password:
            return Response({"message": "Both old and new passwords are required."}, status=status.HTTP_200_OK)

        if not user.check_password(old_password):
            return Response({"message": "Old password is incorrect."}, status=status.HTTP_200_OK)

        if new_password != confirm_password:
            return Response({"message": " New passwords need to be the same."}, status=status.HTTP_200_OK)

        if new_password == old_password:
            return Response({"message": " New password cannot be the same as the old password"}, status=status.HTTP_200_OK)

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
            serializer=UserSerializer(user,context={'request': request})
            return Response({
                "message": "Password updated successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user":serializer.data
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
        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_email = serializer.validated_data.get('email')
        profile_picture = serializer.validated_data.get('profile_picture')
        # profile_picture = serializer.validated_data.get('profile_picture')
        # print(profile_picture)
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
            return Response({"message": "Email verification sent.","user":serializer.data},  status=status.HTTP_200_OK)
        serializer.save()
        return Response({"message":"Profile updated successfully","user":serializer.data}, status=status.HTTP_200_OK)

    """Profile update OTP Verification (if email is changed)"""
    @action(detail=False, methods=['POST'],url_path='new-email-otp-verification')
    def verify_email_otp(self, request):
        email = request.data.get("email")
        new_email = request.data.get("new_email") 
        otp = request.data.get("otp")

        try:
            user = MyUser.objects.get(email=email)
            
            if not hasattr(user, 'updated_email') or not user.updated_email:
                return Response({"message":"No email update request pending"}, status=status.HTTP_400_BAD_REQUEST)
                
            if user.updated_email != new_email:  
                return Response({"message":"Email doesn't match pending update"}, status=status.HTTP_400_BAD_REQUEST)

            if otp != user.otp:
                return Response({"message":"The OTP is invalid"}, status=status.HTTP_400_BAD_REQUEST)

            if user.otp_expiry and timezone.now() > user.otp_expiry:
                return Response({"message":"OTP expired, request a new one"}, status=status.HTTP_400_BAD_REQUEST)

            user.email = user.updated_email
            user.username = user.updated_email
            user.updated_email = None
            user.otp = None
            user.otp_expiry = None
            user.save()

            serializer = UserSerializer(user)
            
            send_mail(
                subject='Verification Successful',
                message=f"Hello {user.first_name}, \n\nYour new email has been verified successfully.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],  
                fail_silently=True
            )

            return Response({
                "message": "Your email was updated successfully",
                "user": serializer.data
            }, status=status.HTTP_200_OK)
            
        except MyUser.DoesNotExist:
            return Response({"message":"User not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['PATCH'], url_path='update-profile-picture', parser_classes=[MultiPartParser, FormParser])
    def update_profile_picture(self, request):
        user = request.user
        
        # Check if file exists in request
        if 'profile_picture' not in request.FILES:
            return Response({"message": "No profile picture provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        profile_picture = request.FILES['profile_picture']
        
        # Validate file size (example: 5MB limit)
        if profile_picture.size > 5 * 1024 * 1024:
            return Response({"message": "File size too large (max 5MB)"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file type
        valid_types = ['image/jpeg', 'image/png', 'image/jpg']
        if profile_picture.content_type not in valid_types:
            return Response({"message": "Invalid file type (only JPEG, JPG, PNG allowed)"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update profile picture
        user.profile_picture = profile_picture
        user.save()
        
        # Return new profile picture URL
        serializer = UserSerializer(user)
        return Response({
            "message": "Profile picture updated successfully",
            "profile_picture_url": user.profile_picture.url,
            "user": serializer.data
        }, status=status.HTTP_200_OK)

    """To allow the users to delete their accounts"""
    @action(detail=False, methods=['DELETE','GET'], url_path='delete-account')
    def delete_account(self,request):
        user = request.user        
        if request.method == 'DELETE':
            user.scheduled_deletion_date = timezone.now() + timedelta(days=7)
            user.save()
            return Response(
                {"message": "Your account is scheduled to be deleted in seven days",
                "is_scheduled_for_deletion": True,
                "scheduled_date": user.scheduled_deletion_date
                 },
                status=status.HTTP_200_OK
            )
        
        elif request.method == 'GET':
            if user.scheduled_deletion_date:
                return Response({
                    "is_scheduled_for_deletion": True,
                    "scheduled_date": user.scheduled_deletion_date,
                    "message": f"Account is scheduled for deletion on {user.scheduled_deletion_date}"
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "is_scheduled_for_deletion": False,
                    "message": "Account is not scheduled for deletion"
                }, status=status.HTTP_200_OK)

    """To allow the users to reverse the account deletion"""
    @action(detail=False, methods=['POST'], url_path='undo-account-deletion')
    def undo_account_deletion(self, request):
        user = request.user
        user.scheduled_deletion_date = None
        user.save()
        return Response({"message": "Your account deletion request has been cancelled.",
        "is_scheduled_for_deletion": False
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_path='logout')
    def logout(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response(
                {"error": "You must be logged in to log out."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                return Response(
                    {"error": "Invalid or expired refresh token."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        request.session.flush()
        return Response({"message": "You have logged out successfully"}, status=status.HTTP_200_OK)

"""For retrieving all the blogs"""
class BlogViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    @action(detail=False, methods=['GET'], url_path='all-blog-items')
    def all_blog_items(self, request):
        blogs=Blog.objects.order_by('-created_at')
        serializer = BlogSerializer(blogs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

"""For retrieving the privacy policy and the terms and conditions"""
class LegalItemsViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    @action(detail=False, methods=['GET'], url_path='legal-items')
    def legal_items(self,request):
        legal_items = LegalItem.objects.first()
        serializer = LegalItemsSerializer(legal_items)
        return Response(serializer.data, status=status.HTTP_200_OK)

"""For retrieving all the available courses"""
class CourseItemsViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in ['course_items']:
            return [AllowAny()]
        return [IsAuthenticated()]
    @action(detail=False, methods=['GET'], url_path='available-courses')
    def course_items(self,request):
        available_courses = Course.objects.all()
        serializer = CourseItemsSerializer(available_courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='structured-available-courses')
    def course_items_structured(self, request):
        courses = Course.objects.all()

        enrolled_course_ids = set()
        if request.user.is_authenticated:
            enrolled_course_ids = set(
                EnrolledCourses.objects.filter(
                    student=request.user,
                    is_enrolled=True
                ).values_list('course_name_id', flat=True)
            )

        grouped_courses = defaultdict(list)

        for course in courses:
            serialized = CourseItemsSerializer(course).data
            serialized['is_enrolled'] = course.id in enrolled_course_ids
            grouped_courses[course.course_name].append(serialized)

        return Response(grouped_courses, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_path='enroll-courses')
    def enroll_course(self, request):
        student = request.user
        serializer = EnrollCourseItemsSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        course_name = serializer.validated_data['course_name']
        course_level = serializer.validated_data['course_level']

        already_enrolled = models.EnrolledCourses.objects.filter(
            student=student,
            course_name=course_name,
            course_level=course_level
        ).exists()

        if already_enrolled:
            return Response(
                {"message": "You are already enrolled in this course."},
                status=status.HTTP_200_OK
            )

        serializer.save()
        return Response({"message":"You have successfully enrolled in this course"}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['GET'], url_path='ongoing-and-completed-courses')
    def ongoing_and_completed_courses(self, request):
        enrolled_courses = EnrolledCourses.objects.filter(
            student=request.user,
            is_enrolled=True
        ).select_related('course_name')


        ongoing_courses = []
        completed_courses = []

        for enrolled in enrolled_courses:
            serialized_course = EnrollCourseItemsSerializer(enrolled).data

            if enrolled.is_completed:
                completed_courses.append(serialized_course)
            else:
                ongoing_courses.append(serialized_course)
        
        graph_serializer = DashboardGraphSerializer()
        
        weekly_lessons_data = graph_serializer.get_weekly_lessons_data(request.user)
        monthly_lessons_data = graph_serializer.get_monthly_lessons_data(request.user)
        
        weekly_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        monthly_common_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


        return Response({
            "ongoing_courses": ongoing_courses,
            "completed_courses": completed_courses,
            "weekly_lessons_data": weekly_lessons_data,
            "lessons_by_month_data": monthly_lessons_data,
            "weekly_labels": weekly_labels,
            "monthly_common_labels": monthly_common_labels
        }, status=status.HTTP_200_OK)

    """Contains all the modules for the course and the respective lessons under them."""
    @action(detail=False, methods=['GET'], url_path='course-modules/(?P<course_id>[^/.]+)')
    def course_modules(self, request, course_id=None):
        enrolled_course = get_object_or_404(
            EnrolledCourses,
            course_name__id=course_id,
            student=request.user
        )

        course_modules = CourseModule.objects.filter(
            course=enrolled_course.course_name
        ).order_by('module_order')

        serializer = CourseModulesSerializer(course_modules, many=True,context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    """Contains all the modules for the course and the respective lessons under them."""

    @action(detail=False, methods=['GET', 'POST'], url_path='course-lesson-completion/(?P<lesson_id>[^/.]+)')
    def lesson_completion(self, request, lesson_id=None):
        lesson = get_object_or_404(CourseLesson, id=lesson_id)
        
        if request.method == 'GET':
            completed = LessonCompletion.objects.filter(
                lesson_student=request.user,
                lesson=lesson
            ).exists()
            return Response({"completed": completed}, status=status.HTTP_200_OK)

        serializer = CourseLessonCompletionSerializer(
            data=request.data,
            context={'request': request, 'lesson': lesson}
        )
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():  # Explicit transaction block
                completion, created = LessonCompletion.objects.get_or_create(
                    lesson_student=request.user,
                    lesson=lesson,
                    defaults=serializer.validated_data
                )

                if not created:
                    completion.delete()
                    return Response(
                        {"completed": False, "message": "Lesson marked incomplete"},
                        status=status.HTTP_200_OK
                    )

                return Response(
                    {"completed": True, "message": "Lesson completed"},
                    status=status.HTTP_201_CREATED
                )

        except Exception as e:
            return Response(
                {"error": "Operation failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


"""For retrieving the Payment Subscription plans"""
class SubscriptionItemsViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    @action(detail=False, methods=['GET'], url_path='subscription-items')
    def legal_items(self, request):
        subscription_items = SubscriptionItem.objects.first()
        serializer = SubscriptionItemsSerializer(subscription_items)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PartnerViewSet(viewsets.ViewSet):
    permission_classes=[IsAuthenticated]
    @action(detail=False, methods=['GET'], url_path='find-partners')
    def find_partners(self, request):
        # Get distinct courses for filter dropdown
        languages = (
            Course.objects
            .values('course_name')
            .annotate(min_id=Min('id'))
            .order_by('course_name')
        )
        
        # Base queryset for users
        users_queryset = MyUser.objects.filter(
            id__in=EnrolledCourses.objects.values('student').distinct().exclude(student=request.user)
        ).prefetch_related(
            Prefetch(
                'students',
                queryset=EnrolledCourses.objects.select_related('course_name')
                .order_by('-enrolment_date'),
                to_attr='courses'
            )
        )
        
        # Apply search filter if query parameter exists
        query = request.GET.get('q')
        if query:
            users_queryset = users_queryset.filter(
                id__in=EnrolledCourses.objects.filter(
                    course_name__course_name__icontains=query
                ).values('student').distinct()
            )
        
        # Serialize the data
        user_serializer = PartnerUserSerializer(users_queryset, many=True)
        course_serializer = CourseItemsSerializer(
            Course.objects.filter(id__in=[c['min_id'] for c in languages]),
            many=True
        )
        
        return Response({
            "data": user_serializer.data,
            "query": query or ""
        }, status=status.HTTP_200_OK)









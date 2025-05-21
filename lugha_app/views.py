from urllib import request

from django.contrib.auth import authenticate
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from lugha_app.models import *
from .serializers import *

# Create your views here.

class UserViewSet(viewsets.ModelViewSet):
    queryset=MyUser.objects.all()
    serializer_class=UserSerializer

    """Users can signup and login easily but have to be logged in to update their details"""
    def get_permissions(self):
        if self.action in ['create','login']:
            return [AllowAny()]
        return [IsAuthenticated()]

    """Ensures that the users can only manipulate their details"""
    def get_object(self):
        user=super().get_object()
        if user!=self.request.user:
            raise PermissionDenied("You can only modify your own details")

    """For user login"""
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

    @action(detail=False, methods=['POST'], permission_classes=[IsAuthenticated], url_path='change-password')
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

        return Response({"message": "Password updated successfully."}, status=200)

    """For updating both the profile details and the profile picture"""
    @action(detail=False, methods=['PATCH'], permission_classes=[IsAuthenticated], url_path='update-profile-details')
    def update_profile(self, request):
        user = request.user
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully", "user": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from django.contrib.auth import password_validation
from rest_framework import serializers
from .import models
from .models import MyUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MyUser
        fields = ['id', 'username', 'email', 'password','first_name','last_name','display_name','phone_number','city','country','profile_picture']

    def create(self, validated_data):
        user=MyUser.objects.create_user(**validated_data)
        return user

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['email','first_name','last_name','display_name', 'phone_number', 'profile_picture']
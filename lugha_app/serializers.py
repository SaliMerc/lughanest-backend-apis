from django.contrib.auth import password_validation
from rest_framework import serializers
from .import models
from .models import MyUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MyUser
        fields = ['id', 'username', 'email', 'password','first_name','last_name','display_name','city','country','is_active','profile_picture','accepted_terms_and_conditions','languages_spoken']

    def create(self, validated_data):
        validated_data.pop('is_active', None)
        user=MyUser.objects.create_user(**validated_data, is_active=False)
        return user

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['email','display_name', 'profile_picture', 'languages_spoken']

class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Blog
        fields = '__all__'

class LegalItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LegalItem
        fields = '__all__'
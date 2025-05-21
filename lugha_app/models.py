from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.utils import timezone

class MyUser(AbstractUser):
    email = models.EmailField(unique=True)
    country=models.CharField(max_length=30,null=True, blank=True)
    city = models.CharField(max_length=30, null=True, blank=True)
    device_info = models.CharField(max_length=30,null=True, blank=True)
    display_name=CharField(unique=True, max_length=255, blank=True, null=True)
    phone_number = models.CharField(unique=True, max_length=255, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']


    def __str__(self):
        return self.email


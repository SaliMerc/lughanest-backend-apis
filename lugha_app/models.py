from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.utils import timezone
from django.utils.text import slugify

class MyUser(AbstractUser):
    email = models.EmailField(unique=True)
    country=models.CharField(max_length=30)
    city = models.CharField(max_length=30, null=True, blank=True)
    device_info = models.CharField(max_length=30,null=True, blank=True)
    display_name=CharField(unique=True, max_length=255, blank=True, null=True)
    phone_number = models.CharField(unique=True, max_length=255, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures', blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True, editable=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def save(self, *args, **kwargs):
        if not self.slug and self.username:
            self.slug = slugify(self.username)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


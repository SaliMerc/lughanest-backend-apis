from django.urls import path,include
from . import views
from .views import *
from rest_framework import routers
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('blogs', BlogViewSet, basename='blogs')
router.register('legal', LegalItemsViewSet, basename='legal')

urlpatterns = [
    path('', include(router.urls)),
]
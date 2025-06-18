from django.urls import path,include
from .views import *
from rest_framework import routers
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('blogs', BlogViewSet, basename='blogs')
router.register('legal', LegalItemsViewSet, basename='legal')
router.register('courses', CourseItemsViewSet, basename='courses')
router.register('subscription', SubscriptionItemsViewSet, basename='subscription')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/google/', GoogleAuthView.as_view()),
]
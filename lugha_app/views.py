from django.http import HttpResponse
from rest_framework import viewsets

from lugha_app.models import *
from .serializers import *

# Create your views here.
def test(request):
    return HttpResponse("test")

class UserModelViewSet(viewsets.ModelViewSet):
    queryset=MyUser.objects.all()
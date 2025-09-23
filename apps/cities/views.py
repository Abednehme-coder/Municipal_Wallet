from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import City, Account
from .serializers import CitySerializer, AccountSerializer


class CityListView(generics.ListAPIView):
    """List all cities"""
    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated]


class CityDetailView(generics.RetrieveAPIView):
    """Retrieve city details"""
    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated]

from rest_framework import serializers
from .models import City, Account


class AccountSerializer(serializers.ModelSerializer):
    """Serializer for Account model"""
    
    class Meta:
        model = Account
        fields = ['id', 'account_name', 'balance', 'currency', 'is_active', 'created_at']


class CitySerializer(serializers.ModelSerializer):
    """Serializer for City model"""
    accounts = AccountSerializer(many=True, read_only=True)
    
    class Meta:
        model = City
        fields = ['id', 'name', 'country', 'state', 'description', 'is_active', 'created_at', 'accounts']

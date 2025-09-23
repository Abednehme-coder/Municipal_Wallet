from rest_framework import serializers
from .models import Transaction
from apps.cities.models import Account
from apps.accounts.models import User


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    approval_progress = serializers.ReadOnlyField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'account', 'city', 'created_by', 'type', 'amount',
            'description', 'status', 'reference', 'metadata', 'created_at',
            'updated_at', 'executed_at', 'created_by_name', 'account_name',
            'city_name', 'approval_progress'
        ]
        read_only_fields = ['id', 'created_by', 'reference', 'status', 'created_at', 'updated_at', 'executed_at']


class TransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transactions"""
    
    class Meta:
        model = Transaction
        fields = ['account', 'type', 'amount', 'description', 'metadata']
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    def validate_account(self, value):
        # Check if account belongs to user's city
        if not self.context['request'].user.role == 'ADMIN':
            if value.city != self.context['request'].user.city:
                raise serializers.ValidationError("Account does not belong to your city")
        return value
    
    def create(self, validated_data):
        validated_data['city'] = validated_data['account'].city
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TransactionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating transactions"""
    
    class Meta:
        model = Transaction
        fields = ['description', 'metadata']
    
    def validate(self, attrs):
        # Only allow updates to pending transactions
        if self.instance.status != 'PENDING':
            raise serializers.ValidationError("Only pending transactions can be updated")
        return attrs


class TransactionCancelSerializer(serializers.Serializer):
    """Serializer for cancelling transactions"""
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        if not self.instance.can_be_cancelled():
            raise serializers.ValidationError("Transaction cannot be cancelled")
        return attrs

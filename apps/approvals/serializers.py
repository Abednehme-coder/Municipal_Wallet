from rest_framework import serializers
from .models import DepositApproval, WithdrawalApproval, RequestApproval


class DepositApprovalSerializer(serializers.ModelSerializer):
    """Serializer for DepositApproval model"""
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)
    transaction_reference = serializers.CharField(source='transaction.reference', read_only=True)
    transaction_amount = serializers.DecimalField(source='transaction.amount', max_digits=15, decimal_places=2, read_only=True)
    transaction_type = serializers.CharField(source='transaction.type', read_only=True)
    
    class Meta:
        model = DepositApproval
        fields = [
            'id', 'transaction', 'approver', 'status', 'comments', 'approved_at',
            'created_at', 'updated_at', 'approver_name', 'transaction_reference',
            'transaction_amount', 'transaction_type'
        ]
        read_only_fields = ['id', 'transaction', 'approver', 'approved_at', 'created_at', 'updated_at']


class RequestApprovalSerializer(serializers.ModelSerializer):
    """Serializer for RequestApproval model using the new 5-role system"""
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)
    approver_role = serializers.CharField(source='approver.role', read_only=True)
    transaction_reference = serializers.CharField(source='transaction.reference', read_only=True)
    transaction_amount = serializers.DecimalField(source='transaction.amount', max_digits=15, decimal_places=2, read_only=True)
    transaction_type = serializers.CharField(source='transaction.type', read_only=True)
    transaction_status = serializers.CharField(source='transaction.status', read_only=True)
    can_be_processed = serializers.SerializerMethodField()
    
    class Meta:
        model = RequestApproval
        fields = [
            'id', 'transaction', 'approver', 'approval_level', 'status', 'comments', 'approved_at',
            'created_at', 'updated_at', 'approver_name', 'approver_role', 'transaction_reference',
            'transaction_amount', 'transaction_type', 'transaction_status', 'can_be_processed'
        ]
        read_only_fields = ['id', 'transaction', 'approver', 'approval_level', 'approved_at', 'created_at', 'updated_at']
    
    def get_can_be_processed(self, obj):
        """Check if this approval can be processed"""
        return obj.can_be_processed()


class WithdrawalApprovalSerializer(serializers.ModelSerializer):
    """Serializer for WithdrawalApproval model"""
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)
    transaction_reference = serializers.CharField(source='transaction.reference', read_only=True)
    transaction_amount = serializers.DecimalField(source='transaction.amount', max_digits=15, decimal_places=2, read_only=True)
    transaction_type = serializers.CharField(source='transaction.type', read_only=True)
    
    class Meta:
        model = WithdrawalApproval
        fields = [
            'id', 'transaction', 'approver', 'status', 'comments', 'approved_at',
            'created_at', 'updated_at', 'approver_name', 'transaction_reference',
            'transaction_amount', 'transaction_type'
        ]
        read_only_fields = ['id', 'transaction', 'approver', 'approved_at', 'created_at', 'updated_at']


class RequestApprovalSerializer(serializers.ModelSerializer):
    """Serializer for RequestApproval model using the new 5-role system"""
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)
    approver_role = serializers.CharField(source='approver.role', read_only=True)
    transaction_reference = serializers.CharField(source='transaction.reference', read_only=True)
    transaction_amount = serializers.DecimalField(source='transaction.amount', max_digits=15, decimal_places=2, read_only=True)
    transaction_type = serializers.CharField(source='transaction.type', read_only=True)
    transaction_status = serializers.CharField(source='transaction.status', read_only=True)
    can_be_processed = serializers.SerializerMethodField()
    
    class Meta:
        model = RequestApproval
        fields = [
            'id', 'transaction', 'approver', 'approval_level', 'status', 'comments', 'approved_at',
            'created_at', 'updated_at', 'approver_name', 'approver_role', 'transaction_reference',
            'transaction_amount', 'transaction_type', 'transaction_status', 'can_be_processed'
        ]
        read_only_fields = ['id', 'transaction', 'approver', 'approval_level', 'approved_at', 'created_at', 'updated_at']
    
    def get_can_be_processed(self, obj):
        """Check if this approval can be processed"""
        return obj.can_be_processed()

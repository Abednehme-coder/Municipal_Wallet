from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'action', 'description', 'details', 'ip_address',
            'user_agent', 'created_at', 'user_name'
        ]
        read_only_fields = ['id', 'created_at']

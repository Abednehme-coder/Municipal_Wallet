from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class AuditLog(models.Model):
    """
    Audit log for tracking all user actions
    """
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('TRANSACTION_CREATED', 'Transaction Created'),
        ('TRANSACTION_UPDATED', 'Transaction Updated'),
        ('TRANSACTION_CANCELLED', 'Transaction Cancelled'),
        ('DEPOSIT_APPROVED', 'Deposit Approved'),
        ('DEPOSIT_REJECTED', 'Deposit Rejected'),
        ('WITHDRAWAL_APPROVED', 'Withdrawal Approved'),
        ('WITHDRAWAL_REJECTED', 'Withdrawal Rejected'),
        ('ACCOUNT_CREATED', 'Account Created'),
        ('ACCOUNT_UPDATED', 'Account Updated'),
        ('USER_CREATED', 'User Created'),
        ('USER_UPDATED', 'User Updated'),
        ('CITY_CREATED', 'City Created'),
        ('CITY_UPDATED', 'City Updated'),
        ('SYSTEM_ACTION', 'System Action'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()
    
    # Generic foreign key for related objects
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']

    def __str__(self):
        user_name = self.user.full_name if self.user else 'System'
        return f"{user_name} - {self.action} - {self.created_at}"

    @classmethod
    def log_action(cls, user, action, description, content_object=None, details=None, request=None):
        """Create an audit log entry"""
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = cls.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        return cls.objects.create(
            user=user,
            action=action,
            description=description,
            content_object=content_object,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

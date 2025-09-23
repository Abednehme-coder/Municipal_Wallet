from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class Notification(models.Model):
    """
    Notification model for users
    """
    NOTIFICATION_TYPE_CHOICES = [
        ('APPROVAL_REQUIRED', 'Approval Required'),
        ('TRANSACTION_APPROVED', 'Transaction Approved'),
        ('TRANSACTION_REJECTED', 'Transaction Rejected'),
        ('TRANSACTION_EXECUTED', 'Transaction Executed'),
        ('TRANSACTION_CANCELLED', 'Transaction Cancelled'),
        ('SYSTEM_ALERT', 'System Alert'),
        ('WEEKLY_REPORT', 'Weekly Report'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    
    # Generic foreign key for related objects
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def create_approval_notification(cls, user, transaction, approver_name):
        """Create approval required notification"""
        return cls.objects.create(
            user=user,
            type='APPROVAL_REQUIRED',
            title=f'Approval Required for {transaction.type}',
            message=f'{approver_name} has requested approval for a {transaction.type.lower()} of ${transaction.amount}',
            content_object=transaction,
            metadata={
                'transaction_id': str(transaction.id),
                'transaction_type': transaction.type,
                'amount': str(transaction.amount),
                'approver_name': approver_name
            }
        )

    @classmethod
    def create_transaction_status_notification(cls, user, transaction, status):
        """Create transaction status notification"""
        type_mapping = {
            'APPROVED': 'TRANSACTION_APPROVED',
            'REJECTED': 'TRANSACTION_REJECTED',
            'EXECUTED': 'TRANSACTION_EXECUTED',
            'CANCELLED': 'TRANSACTION_CANCELLED',
        }
        
        return cls.objects.create(
            user=user,
            type=type_mapping.get(status, 'SYSTEM_ALERT'),
            title=f'Transaction {status.title()}',
            message=f'Your {transaction.type.lower()} of ${transaction.amount} has been {status.lower()}',
            content_object=transaction,
            metadata={
                'transaction_id': str(transaction.id),
                'transaction_type': transaction.type,
                'amount': str(transaction.amount),
                'status': status
            }
        )

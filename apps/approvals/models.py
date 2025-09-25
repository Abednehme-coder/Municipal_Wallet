from django.db import models
from django.utils import timezone


class BaseApproval(models.Model):
    """
    Base approval model for transactions
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    transaction = models.ForeignKey('transactions.Transaction', on_delete=models.CASCADE)
    approver = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    comments = models.TextField(blank=True, null=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.approver.full_name} - {self.transaction.reference} - {self.status}"

    def approve(self, comments=None):
        """Approve the transaction"""
        if self.status != 'PENDING':
            return False
        
        # Additional check: Ensure this user hasn't already approved this transaction
        existing_approval = self.__class__.objects.filter(
            transaction=self.transaction,
            approver=self.approver,
            status__in=['APPROVED', 'REJECTED']
        ).exclude(id=self.id).first()
        
        if existing_approval:
            return False
        
        self.status = 'APPROVED'
        self.comments = comments
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'comments', 'approved_at'])
        
        # Check if transaction can be executed
        from apps.transactions.utils import check_transaction_status
        check_transaction_status(self.transaction)
        
        return True

    def reject(self, comments=None):
        """Reject the transaction"""
        if self.status != 'PENDING':
            return False
        
        # Additional check: Ensure this user hasn't already approved/rejected this transaction
        existing_approval = self.__class__.objects.filter(
            transaction=self.transaction,
            approver=self.approver,
            status__in=['APPROVED', 'REJECTED']
        ).exclude(id=self.id).first()
        
        if existing_approval:
            return False
        
        self.status = 'REJECTED'
        self.comments = comments
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'comments', 'approved_at'])
        
        # Check if transaction should be rejected
        from apps.transactions.utils import check_transaction_status
        check_transaction_status(self.transaction)
        
        return True


class RequestApproval(BaseApproval):
    """
    Approval model for incoming/outgoing requests using the 5-role system
    """
    approval_level = models.IntegerField(help_text="Approval level (1, 2, or 3)")
    
    class Meta:
        db_table = 'request_approvals'
        verbose_name = 'Request Approval'
        verbose_name_plural = 'Request Approvals'
        unique_together = ['transaction', 'approver']
        ordering = ['approval_level', 'created_at']

    def save(self, *args, **kwargs):
        # Automatically set approval level based on approver's role
        if not self.approval_level and self.approver:
            self.approval_level = self.approver.get_approval_level()
        super().save(*args, **kwargs)

    def can_be_processed(self):
        """Check if this approval can be processed - now allows any approver to approve"""
        if self.status != 'PENDING':
            return False
        
        # Any approver can now process their approval regardless of level
        return True


# Keep the old models for backward compatibility during migration
class DepositApproval(BaseApproval):
    """
    Approval model for deposit transactions (legacy)
    """
    class Meta:
        db_table = 'deposit_approvals'
        verbose_name = 'Deposit Approval'
        verbose_name_plural = 'Deposit Approvals'
        unique_together = ['transaction', 'approver']


class WithdrawalApproval(BaseApproval):
    """
    Approval model for withdrawal transactions (legacy)
    """
    class Meta:
        db_table = 'withdrawal_approvals'
        verbose_name = 'Withdrawal Approval'
        verbose_name_plural = 'Withdrawal Approvals'
        unique_together = ['transaction', 'approver']

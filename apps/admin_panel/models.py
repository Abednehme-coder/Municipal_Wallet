from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class ApproverAssignment(models.Model):
    """
    Model to manage dynamic approver assignments for deposits and withdrawals
    Now supports any-order approvals (no level restrictions)
    """
    TRANSACTION_TYPE_CHOICES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]
    
    transaction_type = models.CharField(
        max_length=20, 
        choices=TRANSACTION_TYPE_CHOICES,
        help_text="Type of transaction this approver can approve"
    )
    approver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['APPROVER_1', 'APPROVER_2', 'APPROVER_3', 'APPROVER_4', 'APPROVER_5']},
        help_text="User who can approve this transaction type"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this approver assignment is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['transaction_type', 'approver']
        verbose_name = 'Approver Assignment'
        verbose_name_plural = 'Approver Assignments'
        ordering = ['transaction_type', 'approver__username']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()}: {self.approver.full_name}"
    
    @classmethod
    def get_approvers_for_transaction_type(cls, transaction_type, active_only=True):
        """Get all approvers for a specific transaction type"""
        queryset = cls.objects.filter(transaction_type=transaction_type)
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset.order_by('approver__username')
    
    @classmethod
    def get_required_approvers_count(cls, transaction_type):
        """Get the number of required approvers for a transaction type"""
        return cls.get_approvers_for_transaction_type(transaction_type).count()
    
    @classmethod
    def ensure_approver_assignments(cls):
        """Ensure approvers are assigned for both transaction types"""
        for transaction_type in ['DEPOSIT', 'WITHDRAWAL']:
            # Get all available approvers
            approvers = User.objects.filter(
                role__in=['APPROVER_1', 'APPROVER_2', 'APPROVER_3', 'APPROVER_4', 'APPROVER_5'],
                is_active=True
            )
            
            for approver in approvers:
                assignment, created = cls.objects.get_or_create(
                    transaction_type=transaction_type,
                    approver=approver,
                    defaults={'is_active': True}
                )


class ApprovalConfiguration(models.Model):
    """
    Model to store configuration for approval requirements
    """
    TRANSACTION_TYPE_CHOICES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        unique=True
    )
    required_approvals = models.PositiveIntegerField(
        default=3,
        help_text="Number of approvals required for this transaction type"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this configuration is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Approval Configuration'
        verbose_name_plural = 'Approval Configurations'
    
    def __str__(self):
        return f"{self.get_transaction_type_display()}: {self.required_approvals} approvals"
    
    @classmethod
    def get_required_approvals(cls, transaction_type):
        """Get the required number of approvals for a transaction type"""
        try:
            config = cls.objects.get(transaction_type=transaction_type, is_active=True)
            return config.required_approvals
        except cls.DoesNotExist:
            # Default values
            return 3 if transaction_type == 'DEPOSIT' else 5

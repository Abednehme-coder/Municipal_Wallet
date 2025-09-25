from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid


class Transaction(models.Model):
    """
    Transaction model for deposits and withdrawals
    """
    TRANSACTION_TYPE_CHOICES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('EXECUTED', 'Executed'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey('cities.Account', on_delete=models.CASCADE, related_name='transactions')
    city = models.ForeignKey('cities.City', on_delete=models.CASCADE, related_name='transactions')
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='created_transactions')
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    reference = models.CharField(max_length=50, unique=True, blank=True)
    
    # Depositor information (for deposits only)
    depositor_name = models.CharField(max_length=255, blank=True, null=True, help_text="Name of the person making the deposit")
    depositor_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Phone number of the depositor")
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} - {self.amount} - {self.account.city.name}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        super().save(*args, **kwargs)

    def generate_reference(self):
        """Generate incremental transaction reference starting from 1"""
        # Get the highest reference number for this transaction type
        prefix = 'DEP' if self.type == 'DEPOSIT' else 'WTH'
        
        # Find the highest numeric reference for this type
        existing_refs = Transaction.objects.filter(
            reference__startswith=prefix
        ).exclude(
            reference__isnull=True
        ).exclude(reference='')
        
        max_num = 0
        for ref in existing_refs:
            try:
                # Extract number from reference (e.g., "DEP-123" -> 123)
                num_part = ref.reference.split('-')[1] if '-' in ref.reference else ref.reference[3:]
                num = int(num_part)
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        
        # Return next number
        next_num = max_num + 1
        return f"{prefix}-{next_num:06d}"  # Format as 6-digit number with leading zeros

    def can_be_cancelled(self):
        """Check if transaction can be cancelled"""
        return self.status == 'PENDING'

    def can_be_executed(self):
        """Check if transaction can be executed"""
        return self.status == 'APPROVED'

    def execute(self):
        """Execute the transaction"""
        if not self.can_be_executed():
            return False

        if self.type == 'DEPOSIT':
            self.account.deposit(self.amount)
        else:  # WITHDRAWAL
            if not self.account.withdraw(self.amount):
                return False

        self.status = 'EXECUTED'
        self.executed_at = timezone.now()
        self.save(update_fields=['status', 'executed_at'])
        return True

    def cancel(self, reason=None):
        """Cancel the transaction"""
        if not self.can_be_cancelled():
            return False

        self.status = 'CANCELLED'
        if reason:
            self.metadata['cancellation_reason'] = reason
        self.save(update_fields=['status', 'metadata'])
        return True

    @property
    def approval_progress(self):
        """Get approval progress for this transaction"""
        from .utils import get_approval_progress
        return get_approval_progress(self)

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
        """Generate unique transaction reference"""
        import random
        import string
        prefix = 'DEP' if self.type == 'DEPOSIT' else 'WTH'
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"{prefix}-{random_str}"

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

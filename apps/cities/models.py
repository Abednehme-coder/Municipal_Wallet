from django.db import models
from django.core.validators import MinLengthValidator


class City(models.Model):
    """
    City model for municipal wallet system
    """
    name = models.CharField(max_length=200, unique=True)
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cities'
        verbose_name = 'City'
        verbose_name_plural = 'Cities'
        ordering = ['name']

    def __str__(self):
        return f"{self.name}, {self.state or self.country}"

    @property
    def full_name(self):
        if self.state:
            return f"{self.name}, {self.state}, {self.country}"
        return f"{self.name}, {self.country}"


class Account(models.Model):
    """
    Financial account for a city
    """
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('CAD', 'Canadian Dollar'),
        ('AUD', 'Australian Dollar'),
    ]

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='accounts')
    account_name = models.CharField(max_length=200)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts'
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.account_name} - {self.city.name}"

    def can_withdraw(self, amount):
        """Check if account has sufficient balance for withdrawal"""
        return self.balance >= amount

    def deposit(self, amount):
        """Add amount to account balance"""
        self.balance += amount
        self.save(update_fields=['balance', 'updated_at'])

    def withdraw(self, amount):
        """Subtract amount from account balance"""
        if self.can_withdraw(amount):
            self.balance -= amount
            self.save(update_fields=['balance', 'updated_at'])
            return True
        return False

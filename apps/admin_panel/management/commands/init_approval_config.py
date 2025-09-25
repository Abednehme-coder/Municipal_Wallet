from django.core.management.base import BaseCommand
from apps.admin_panel.models import ApproverAssignment, ApprovalConfiguration


class Command(BaseCommand):
    help = 'Initialize approval configurations based on active approvers'

    def handle(self, *args, **options):
        """Initialize approval configurations for both transaction types"""
        
        # Process deposits
        active_deposit_count = ApproverAssignment.objects.filter(
            transaction_type='DEPOSIT',
            is_active=True
        ).count()
        
        deposit_config, created = ApprovalConfiguration.objects.get_or_create(
            transaction_type='DEPOSIT',
            defaults={'required_approvals': active_deposit_count}
        )
        
        if not created:
            deposit_config.required_approvals = active_deposit_count
            deposit_config.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'Deposit configuration: {active_deposit_count} required approvals')
        )
        
        # Process withdrawals
        active_withdrawal_count = ApproverAssignment.objects.filter(
            transaction_type='WITHDRAWAL',
            is_active=True
        ).count()
        
        withdrawal_config, created = ApprovalConfiguration.objects.get_or_create(
            transaction_type='WITHDRAWAL',
            defaults={'required_approvals': active_withdrawal_count}
        )
        
        if not created:
            withdrawal_config.required_approvals = active_withdrawal_count
            withdrawal_config.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'Withdrawal configuration: {active_withdrawal_count} required approvals')
        )
        
        self.stdout.write(
            self.style.SUCCESS('Approval configurations initialized successfully!')
        )

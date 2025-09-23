from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.cities.models import City, Account
from apps.transactions.models import Transaction
from apps.approvals.models import RequestApproval
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create essential data for the 5-role system (cities, accounts, and users)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing data and create fresh data',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting existing data...')
            # Clear existing data
            Transaction.objects.all().delete()
            RequestApproval.objects.all().delete()
            Account.objects.all().delete()
            City.objects.all().delete()
            User.objects.all().delete()

        # Create essential cities
        self.create_essential_cities()
        
        # Create the 5 required users
        self.create_role_users()
        
        # Create basic accounts
        self.create_basic_accounts()

        self.stdout.write(
            self.style.SUCCESS('Successfully created essential data for the 5-role system!')
        )

    def create_essential_cities(self):
        """Create essential cities for the system"""
        cities_data = [
            {
                'name': 'Municipal City',
                'country': 'United States',
                'state': 'State',
                'description': 'Main municipal city for the wallet system'
            }
        ]
        
        for city_data in cities_data:
            city, created = City.objects.get_or_create(
                name=city_data['name'],
                defaults=city_data
            )
            if created:
                self.stdout.write(f'Created city: {city.name}')
            else:
                self.stdout.write(f'City already exists: {city.name}')

    def create_role_users(self):
        """Create the 5 required users for the role system"""
        # Ensure exactly one user per role
        User.ensure_single_user_per_role()

        # Create specific users for each role
        roles_data = [
            {
                'role': 'INITIATOR',
                'email': 'initiator@municipal.gov',
                'first_name': 'John',
                'last_name': 'Initiator',
                'password': 'initiator123'
            },
            {
                'role': 'APPROVER_1',
                'email': 'approver1@municipal.gov',
                'first_name': 'Jane',
                'last_name': 'Approver1',
                'password': 'approver1123'
            },
            {
                'role': 'APPROVER_2',
                'email': 'approver2@municipal.gov',
                'first_name': 'Bob',
                'last_name': 'Approver2',
                'password': 'approver2123'
            },
            {
                'role': 'APPROVER_3',
                'email': 'approver3@municipal.gov',
                'first_name': 'Alice',
                'last_name': 'Approver3',
                'password': 'approver3123'
            }
        ]

        # Get the main city
        main_city = City.objects.first()
        
        for role_data in roles_data:
            user, created = User.objects.get_or_create(
                email=role_data['email'],
                defaults={
                    'first_name': role_data['first_name'],
                    'last_name': role_data['last_name'],
                    'role': role_data['role'],
                    'city': main_city,
                    'is_active': True
                }
            )
            
            if created:
                user.set_password(role_data['password'])
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created {role_data["role"]} user: {user.email}')
                )
            else:
                # Update existing user
                user.first_name = role_data['first_name']
                user.last_name = role_data['last_name']
                user.role = role_data['role']
                user.city = main_city
                user.is_active = True
                user.set_password(role_data['password'])
                user.save()
                self.stdout.write(
                    self.style.WARNING(f'Updated {role_data["role"]} user: {user.email}')
                )

        # Verify exactly one user per role
        self.stdout.write('\nVerifying role assignments...')
        for role_code, role_name in User.ROLE_CHOICES:
            users_with_role = User.objects.filter(role=role_code, is_active=True)
            count = users_with_role.count()
            if count == 1:
                user = users_with_role.first()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {role_name}: {user.email}')
                )
            elif count == 0:
                self.stdout.write(
                    self.style.ERROR(f'✗ {role_name}: No user assigned')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ {role_name}: {count} users assigned (should be 1)')
                )

    def create_basic_accounts(self):
        """Create basic accounts for the main city"""
        main_city = City.objects.first()
        if not main_city:
            self.stdout.write(self.style.ERROR('No city found. Please create a city first.'))
            return

        # Create a basic general fund account
        account, created = Account.objects.get_or_create(
            city=main_city,
            account_name='General Fund',
            defaults={
                'balance': Decimal('0.00'),
                'currency': 'USD'
            }
        )
        
        if created:
            self.stdout.write(f'Created General Fund account for {main_city.name}')
        else:
            self.stdout.write(f'General Fund account already exists for {main_city.name}')

        self.stdout.write('\nLogin credentials:')
        self.stdout.write('INITIATOR: initiator@municipal.gov / initiator123')
        self.stdout.write('APPROVER_1: approver1@municipal.gov / approver1123')
        self.stdout.write('APPROVER_2: approver2@municipal.gov / approver2123')
        self.stdout.write('APPROVER_3: approver3@municipal.gov / approver3123')

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import User

User = get_user_model()


class Command(BaseCommand):
    help = 'Create the 5 required users for the role-based system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing users and create new ones',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting existing users...')
            User.objects.all().delete()

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

        for role_data in roles_data:
            user, created = User.objects.get_or_create(
                email=role_data['email'],
                defaults={
                    'first_name': role_data['first_name'],
                    'last_name': role_data['last_name'],
                    'role': role_data['role'],
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

        self.stdout.write(
            self.style.SUCCESS('\n5-role system setup complete!')
        )
        self.stdout.write('\nLogin credentials:')
        for role_data in roles_data:
            self.stdout.write(f'{role_data["role"]}: {role_data["email"]} / {role_data["password"]}')

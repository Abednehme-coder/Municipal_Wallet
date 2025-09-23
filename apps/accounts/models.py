from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator


class UserManager(BaseUserManager):
    """Custom user manager for the User model"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model for municipal wallet system
    """
    ROLE_CHOICES = [
        ('INITIATOR', 'Initiator'),
        ('APPROVER_1', 'Approver Level 1'),
        ('APPROVER_2', 'Approver Level 2'),
        ('APPROVER_3', 'Approver Level 3'),
        ('APPROVER_4', 'Approver Level 4'),
        ('APPROVER_5', 'Approver Level 5'),
    ]

    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='INITIATOR')
    city = models.ForeignKey('cities.City', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    phone_number = models.CharField(
        max_length=17,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )],
        blank=True,
        null=True
    )
    two_factor_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def can_create_requests(self):
        """Check if user can create incoming/outgoing requests"""
        return self.role == 'INITIATOR'

    def can_approve_requests(self):
        """Check if user can approve requests"""
        return self.role in ['APPROVER_1', 'APPROVER_2', 'APPROVER_3', 'APPROVER_4', 'APPROVER_5']

    def get_approval_level(self):
        """Get the approval level for this user"""
        if self.role == 'APPROVER_1':
            return 1
        elif self.role == 'APPROVER_2':
            return 2
        elif self.role == 'APPROVER_3':
            return 3
        elif self.role == 'APPROVER_4':
            return 4
        elif self.role == 'APPROVER_5':
            return 5
        return None

    @classmethod
    def get_user_by_role(cls, role):
        """Get the single user assigned to a specific role"""
        try:
            return cls.objects.get(role=role, is_active=True)
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # This should not happen in our system
            return cls.objects.filter(role=role, is_active=True).first()

    @classmethod
    def ensure_single_user_per_role(cls):
        """Ensure exactly one user exists for each role"""
        for role_code, role_name in cls.ROLE_CHOICES:
            users_with_role = cls.objects.filter(role=role_code, is_active=True)
            if users_with_role.count() == 0:
                # Create a default user for this role if none exists
                cls.objects.create(
                    email=f"{role_code.lower()}@municipal.gov",
                    first_name=f"{role_name}",
                    last_name="User",
                    role=role_code,
                    is_active=True
                )
            elif users_with_role.count() > 1:
                # Keep only the first user, deactivate others
                first_user = users_with_role.first()
                users_with_role.exclude(id=first_user.id).update(is_active=False)

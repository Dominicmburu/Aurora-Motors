from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone
from apps.core.models import TimeStampedModel

class CustomUser(AbstractUser):
    """Custom user model extending Django's AbstractUser"""
    
    USER_TYPES = (
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    )
    
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='customer')
    is_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='users/avatars/', blank=True, null=True)
    
    # Profile completion
    profile_completed = models.BooleanField(default=False)
    
    # Preferences
    receive_notifications = models.BooleanField(default=True)
    receive_marketing = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def get_absolute_url(self):
        return reverse('accounts:profile', kwargs={'pk': self.pk})
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def get_short_name(self):
        return self.first_name or self.username
    
    @property
    def is_customer(self):
        return self.user_type == 'customer'
    
    @property
    def is_staff_member(self):
        return self.user_type == 'staff'
    
    @property
    def is_admin_user(self):
        return self.user_type == 'admin' or self.is_superuser
    
    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    def can_book_vehicle(self):
        """Check if user can book a vehicle"""
        if not self.is_verified:
            return False, "Account not verified"
        
        if not self.profile_completed:
            return False, "Profile not completed"
        
        if self.age and self.age < 18:
            return False, "Must be 18 or older"
        
        # Check if user has any active bookings that are overdue
        from apps.bookings.models import Booking
        overdue_bookings = Booking.objects.filter(
            user=self,
            status='confirmed',
            end_date__lt=timezone.now()
        ).exists()
        
        if overdue_bookings:
            return False, "You have overdue bookings"
        
        return True, "Can book"


class UserProfile(TimeStampedModel):
    """Extended user profile information"""
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    
    # Emergency contact
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    
    # Driver information
    license_number = models.CharField(max_length=50, blank=True)
    license_expiry = models.DateField(null=True, blank=True)
    license_country = models.CharField(max_length=50, blank=True)
    
    # Company information (for business customers)
    company_name = models.CharField(max_length=200, blank=True)
    company_abn = models.CharField(max_length=20, blank=True)
    company_address = models.TextField(blank=True)
    
    # Statistics
    total_bookings = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Preferences
    preferred_vehicle_type = models.CharField(max_length=50, blank=True)
    preferred_transmission = models.CharField(max_length=20, blank=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Profile"
    
    @property
    def is_license_valid(self):
        if not self.license_expiry:
            return False
        return self.license_expiry > timezone.now().date()


class UserActivity(TimeStampedModel):
    """Track user activities for security and analytics"""
    
    ACTIVITY_TYPES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),
        ('profile_update', 'Profile Update'),
        ('booking_created', 'Booking Created'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('document_uploaded', 'Document Uploaded'),
        ('contract_signed', 'Contract Signed'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_activity_type_display()}"
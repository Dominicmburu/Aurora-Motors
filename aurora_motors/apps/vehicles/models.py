from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedModel

class VehicleCategory(TimeStampedModel):
    """Vehicle category model"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Vehicle Category'
        verbose_name_plural = 'Vehicle Categories'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class VehicleBrand(TimeStampedModel):
    """Vehicle brand model"""
    
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='vehicles/brands/', blank=True, null=True)
    country = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Vehicle Brand'
        verbose_name_plural = 'Vehicle Brands'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Vehicle(TimeStampedModel):
    """Vehicle model"""
    
    TRANSMISSION_CHOICES = (
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('cvt', 'CVT'),
    )
    
    FUEL_TYPE_CHOICES = (
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('hybrid', 'Hybrid'),
        ('electric', 'Electric'),
    )
    
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('rented', 'Rented'),
        ('maintenance', 'Under Maintenance'),
        ('out_of_service', 'Out of Service'),
    )
    
    CONDITION_CHOICES = (
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    )
    
    # Basic Information
    name = models.CharField(max_length=200)
    brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE, related_name='vehicles')
    category = models.ForeignKey(VehicleCategory, on_delete=models.CASCADE, related_name='vehicles')
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(timezone.now().year + 1)]
    )
    
    # Technical Specifications
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPE_CHOICES)
    engine_size = models.DecimalField(max_digits=3, decimal_places=1, help_text="Engine size in liters")
    seats = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)])
    doors = models.PositiveIntegerField(validators=[MinValueValidator(2), MaxValueValidator(10)])
    
    # Vehicle Details
    registration_number = models.CharField(max_length=20, unique=True)
    vin = models.CharField(max_length=17, unique=True, verbose_name="VIN")
    color = models.CharField(max_length=50)
    mileage = models.PositiveIntegerField(help_text="Current mileage in kilometers")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    
    # Pricing
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    weekly_rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    monthly_rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    security_deposit = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Status and Availability
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Maintenance Information
    last_service_date = models.DateField(blank=True, null=True)
    next_service_date = models.DateField(blank=True, null=True)
    last_service_mileage = models.PositiveIntegerField(blank=True, null=True)
    next_service_mileage = models.PositiveIntegerField(blank=True, null=True)
    
    # Insurance Information
    insurance_company = models.CharField(max_length=200, blank=True)
    insurance_policy = models.CharField(max_length=100, blank=True)
    insurance_expiry = models.DateField(blank=True, null=True)
    
    # Additional Information
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Internal notes")
    
    # Location
    location = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['brand', 'model']),
            models.Index(fields=['category']),
            models.Index(fields=['daily_rate']),
        ]
    
    def __str__(self):
        return f"{self.brand.name} {self.model} ({self.year}) - {self.registration_number}"
    
    def get_absolute_url(self):
        return reverse('vehicles:detail', kwargs={'pk': self.pk})
    
    @property
    def full_name(self):
        return f"{self.brand.name} {self.model} ({self.year})"
    
    @property
    def is_available(self):
        return self.status == 'available' and self.is_active
    
    @property
    def needs_service(self):
        if self.next_service_date and self.next_service_date <= timezone.now().date():
            return True
        if self.next_service_mileage and self.mileage >= self.next_service_mileage:
            return True
        return False
    
    @property
    def insurance_expired(self):
        if self.insurance_expiry:
            return self.insurance_expiry <= timezone.now().date()
        return False
    
    def get_rate_for_duration(self, days):
        """Calculate rate based on duration"""
        if days >= 30 and self.monthly_rate:
            months = days // 30
            remaining_days = days % 30
            return (months * self.monthly_rate) + (remaining_days * self.daily_rate)
        elif days >= 7 and self.weekly_rate:
            weeks = days // 7
            remaining_days = days % 7
            return (weeks * self.weekly_rate) + (remaining_days * self.daily_rate)
        else:
            return days * self.daily_rate
    
    def is_available_for_period(self, start_date, end_date):
        """Check if vehicle is available for a specific period"""
        if not self.is_available:
            return False
        
        from apps.bookings.models import Booking
        overlapping_bookings = Booking.objects.filter(
            vehicle=self,
            status__in=['confirmed', 'active'],
            start_date__lt=end_date,
            end_date__gt=start_date
        ).exists()
        
        return not overlapping_bookings


class VehicleImage(TimeStampedModel):
    """Vehicle image model"""
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='vehicles/images/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Vehicle Image'
        verbose_name_plural = 'Vehicle Images'
        ordering = ['sort_order', '-is_primary']
    
    def __str__(self):
        return f"{self.vehicle.full_name} - Image {self.id}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per vehicle
        if self.is_primary:
            VehicleImage.objects.filter(
                vehicle=self.vehicle, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class VehicleFeature(TimeStampedModel):
    """Vehicle feature model"""
    
    FEATURE_TYPES = (
        ('safety', 'Safety'),
        ('comfort', 'Comfort'),
        ('technology', 'Technology'),
        ('performance', 'Performance'),
        ('convenience', 'Convenience'),
    )
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    feature_type = models.CharField(max_length=20, choices=FEATURE_TYPES)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Vehicle Feature'
        verbose_name_plural = 'Vehicle Features'
        ordering = ['feature_type', 'name']
    
    def __str__(self):
        return self.name


class VehicleFeatureAssignment(models.Model):
    """Many-to-many through model for vehicle features"""
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    feature = models.ForeignKey(VehicleFeature, on_delete=models.CASCADE)
    value = models.CharField(max_length=100, blank=True, help_text="Optional feature value")
    
    class Meta:
        unique_together = ['vehicle', 'feature']
        verbose_name = 'Vehicle Feature Assignment'
        verbose_name_plural = 'Vehicle Feature Assignments'
    
    def __str__(self):
        return f"{self.vehicle.full_name} - {self.feature.name}"


# Add many-to-many relationship
Vehicle.add_to_class(
    'features',
    models.ManyToManyField(
        VehicleFeature,
        through=VehicleFeatureAssignment,
        blank=True,
        related_name='vehicles'
    )
)


class VehicleReview(TimeStampedModel):
    """Vehicle review model"""
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='vehicle_reviews')
    booking = models.OneToOneField('bookings.Booking', on_delete=models.CASCADE, related_name='review')
    
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Detailed ratings
    cleanliness_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True
    )
    comfort_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True
    )
    performance_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True
    )
    
    is_approved = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Vehicle Review'
        verbose_name_plural = 'Vehicle Reviews'
        ordering = ['-created_at']
        unique_together = ['vehicle', 'user', 'booking']
    
    def __str__(self):
        return f"{self.vehicle.full_name} - {self.rating}★ by {self.user.get_full_name()}"


class VehicleMaintenanceRecord(TimeStampedModel):
    """Vehicle maintenance record model"""
    
    MAINTENANCE_TYPES = (
        ('service', 'Regular Service'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection'),
        ('cleaning', 'Cleaning'),
        ('tire_change', 'Tire Change'),
        ('oil_change', 'Oil Change'),
        ('other', 'Other'),
    )
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='maintenance_records')
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPES)
    description = models.TextField()
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    mileage_at_service = models.PositiveIntegerField()
    service_date = models.DateField()
    next_service_date = models.DateField(blank=True, null=True)
    next_service_mileage = models.PositiveIntegerField(blank=True, null=True)
    
    # Service provider information
    service_provider = models.CharField(max_length=200)
    service_provider_contact = models.CharField(max_length=100, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    
    # Internal tracking
    performed_by = models.ForeignKey(
        'accounts.CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='performed_maintenance'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Vehicle Maintenance Record'
        verbose_name_plural = 'Vehicle Maintenance Records'
        ordering = ['-service_date']
    
    def __str__(self):
        return f"{self.vehicle.full_name} - {self.get_maintenance_type_display()} ({self.service_date})"
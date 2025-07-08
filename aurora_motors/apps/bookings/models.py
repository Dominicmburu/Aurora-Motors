from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.core.models import TimeStampedModel

class Booking(TimeStampedModel):
    """Booking model"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    )
    
    CANCELLATION_REASONS = (
        ('customer_request', 'Customer Request'),
        ('vehicle_unavailable', 'Vehicle Unavailable'),
        ('payment_failed', 'Payment Failed'),
        ('policy_violation', 'Policy Violation'),
        ('other', 'Other'),
    )
    
    # Basic booking information
    booking_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='bookings')
    vehicle = models.ForeignKey('vehicles.Vehicle', on_delete=models.CASCADE, related_name='bookings')
    
    # Booking dates and times
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    pickup_location = models.CharField(max_length=200)
    return_location = models.CharField(max_length=200)
    
    # Pricing information
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    total_days = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=8, decimal_places=2)
    additional_fees = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    confirmation_date = models.DateTimeField(null=True, blank=True)
    pickup_date = models.DateTimeField(null=True, blank=True)
    return_date = models.DateTimeField(null=True, blank=True)
    
    # Cancellation information
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        'accounts.CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='cancelled_bookings'
    )
    cancellation_reason = models.CharField(
        max_length=50, 
        choices=CANCELLATION_REASONS, 
        null=True, 
        blank=True
    )
    cancellation_notes = models.TextField(blank=True)
    
    # Additional information
    special_requests = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    # Driver information
    primary_driver_license = models.CharField(max_length=50, blank=True)
    additional_drivers = models.ManyToManyField(
        'accounts.CustomUser',
        through='BookingAdditionalDriver',
        blank=True,
        related_name='additional_driver_bookings'
    )
    
    # Mileage tracking
    pickup_mileage = models.PositiveIntegerField(null=True, blank=True)
    return_mileage = models.PositiveIntegerField(null=True, blank=True)
    mileage_limit = models.PositiveIntegerField(default=200, help_text="Daily mileage limit")
    excess_mileage_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.25'),
        help_text="Rate per km over limit"
    )
    
    # Insurance and protection
    insurance_selected = models.BooleanField(default=False)
    insurance_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['vehicle', 'start_date']),
            models.Index(fields=['booking_number']),
        ]
    
    def __str__(self):
        return f"Booking {self.booking_number} - {self.user.get_full_name()}"
    
    def get_absolute_url(self):
        return reverse('bookings:detail', kwargs={'pk': self.pk})
    
    def clean(self):
        """Validate booking data"""
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError('End date must be after start date.')
            
            if self.start_date < timezone.now():
                raise ValidationError('Start date cannot be in the past.')
            
            # Check for booking conflicts
            overlapping_bookings = Booking.objects.filter(
                vehicle=self.vehicle,
                status__in=['confirmed', 'active'],
                start_date__lt=self.end_date,
                end_date__gt=self.start_date
            ).exclude(pk=self.pk)
            
            if overlapping_bookings.exists():
                raise ValidationError('Vehicle is not available for the selected dates.')
    
    def save(self, *args, **kwargs):
        if not self.booking_number:
            self.booking_number = self.generate_booking_number()
        
        # Calculate total days
        if self.start_date and self.end_date:
            self.total_days = (self.end_date.date() - self.start_date.date()).days
            if self.total_days == 0:
                self.total_days = 1  # Minimum 1 day
        
        # Calculate amounts
        self.calculate_amounts()
        
        super().save(*args, **kwargs)
    
    def generate_booking_number(self):
        """Generate unique booking number"""
        import random
        import string
        
        prefix = 'BK'
        year = timezone.now().year
        random_part = ''.join(random.choices(string.digits, k=6))
        
        booking_number = f"{prefix}{year}{random_part}"
        
        # Ensure uniqueness
        while Booking.objects.filter(booking_number=booking_number).exists():
            random_part = ''.join(random.choices(string.digits, k=6))
            booking_number = f"{prefix}{year}{random_part}"
        
        return booking_number
    
    def calculate_amounts(self):
        """Calculate booking amounts"""
        if self.vehicle and self.total_days:
            # Get vehicle rates
            self.daily_rate = self.vehicle.daily_rate
            self.security_deposit = self.vehicle.security_deposit
            
            # Calculate subtotal based on duration
            self.subtotal = self.vehicle.get_rate_for_duration(self.total_days)
            
            # Calculate total
            self.total_amount = (
                self.subtotal + 
                self.additional_fees + 
                self.insurance_amount - 
                self.discount_amount
            )
    
    @property
    def duration(self):
        """Get booking duration"""
        if self.start_date and self.end_date:
            return self.end_date - self.start_date
        return None
    
    @property
    def is_active(self):
        """Check if booking is currently active"""
        now = timezone.now()
        return (
            self.status == 'active' and 
            self.start_date <= now <= self.end_date
        )
    
    @property
    def is_overdue(self):
        """Check if booking is overdue"""
        return (
            self.status in ['confirmed', 'active'] and 
            self.end_date < timezone.now()
        )
    
    @property
    def can_be_cancelled(self):
        """Check if booking can be cancelled"""
        if self.status not in ['pending', 'confirmed']:
            return False
        
        # Check cancellation policy (e.g., can't cancel within 24 hours)
        hours_until_pickup = (self.start_date - timezone.now()).total_seconds() / 3600
        return hours_until_pickup > 24
    
    @property
    def excess_mileage(self):
        """Calculate excess mileage"""
        if self.pickup_mileage and self.return_mileage:
            total_mileage = self.return_mileage - self.pickup_mileage
            allowed_mileage = self.mileage_limit * self.total_days
            return max(0, total_mileage - allowed_mileage)
        return 0
    
    @property
    def excess_mileage_fee(self):
        """Calculate excess mileage fee"""
        return self.excess_mileage * self.excess_mileage_rate
    
    def confirm_booking(self):
        """Confirm the booking"""
        if self.status == 'pending':
            self.status = 'confirmed'
            self.confirmation_date = timezone.now()
            self.save(update_fields=['status', 'confirmation_date'])
    
    def start_rental(self, pickup_mileage=None):
        """Start the rental"""
        if self.status == 'confirmed':
            self.status = 'active'
            self.pickup_date = timezone.now()
            if pickup_mileage:
                self.pickup_mileage = pickup_mileage
            self.save(update_fields=['status', 'pickup_date', 'pickup_mileage'])
            
            # Update vehicle status
            self.vehicle.status = 'rented'
            self.vehicle.save(update_fields=['status'])
    
    def complete_rental(self, return_mileage=None):
        """Complete the rental"""
        if self.status == 'active':
            self.status = 'completed'
            self.return_date = timezone.now()
            if return_mileage:
                self.return_mileage = return_mileage
            self.save(update_fields=['status', 'return_date', 'return_mileage'])
            
            # Update vehicle status
            self.vehicle.status = 'available'
            self.vehicle.mileage = return_mileage or self.vehicle.mileage
            self.vehicle.save(update_fields=['status', 'mileage'])
    
    def cancel_booking(self, cancelled_by, reason, notes=''):
        """Cancel the booking"""
        if self.can_be_cancelled:
            self.status = 'cancelled'
            self.cancelled_at = timezone.now()
            self.cancelled_by = cancelled_by
            self.cancellation_reason = reason
            self.cancellation_notes = notes
            self.save(update_fields=[
                'status', 'cancelled_at', 'cancelled_by', 
                'cancellation_reason', 'cancellation_notes'
            ])


class BookingAdditionalDriver(TimeStampedModel):
    """Additional drivers for a booking"""
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    driver = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    license_number = models.CharField(max_length=50)
    license_expiry = models.DateField()
    is_approved = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['booking', 'driver']
        verbose_name = 'Additional Driver'
        verbose_name_plural = 'Additional Drivers'
    
    def __str__(self):
        return f"{self.driver.get_full_name()} - {self.booking.booking_number}"


class BookingExtension(TimeStampedModel):
    """Booking extension requests"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='extensions')
    original_end_date = models.DateTimeField()
    new_end_date = models.DateTimeField()
    additional_days = models.PositiveIntegerField()
    additional_amount = models.DecimalField(max_digits=8, decimal_places=2)
    reason = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_extensions'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Booking Extension'
        verbose_name_plural = 'Booking Extensions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Extension for {self.booking.booking_number}"
    
    def approve(self, processed_by, notes=''):
        """Approve the extension"""
        self.status = 'approved'
        self.processed_by = processed_by
        self.processed_at = timezone.now()
        self.processing_notes = notes
        self.save()
        
        # Update the original booking
        self.booking.end_date = self.new_end_date
        self.booking.total_days += self.additional_days
        self.booking.total_amount += self.additional_amount
        self.booking.save()
    
    def reject(self, processed_by, notes=''):
        """Reject the extension"""
        self.status = 'rejected'
        self.processed_by = processed_by
        self.processed_at = timezone.now()
        self.processing_notes = notes
        self.save()


class BookingInvoice(TimeStampedModel):
    """Booking invoice model"""
    
    INVOICE_TYPES = (
        ('booking', 'Booking Invoice'),
        ('extension', 'Extension Invoice'),
        ('additional_fees', 'Additional Fees'),
        ('damage', 'Damage Charges'),
    )
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=20, unique=True)
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPES, default='booking')
    
    # Invoice details
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Invoice content
    description = models.TextField()
    line_items = models.JSONField(default=list)
    
    # Status
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateTimeField(null=True, blank=True)
    
    # File
    pdf_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Booking Invoice'
        verbose_name_plural = 'Booking Invoices'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.booking.booking_number}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        
        # Set due date if not provided
        if not self.due_date:
            self.due_date = self.issue_date + timezone.timedelta(days=30)
        
        # Calculate total amount
        self.total_amount = self.amount + self.tax_amount
        
        super().save(*args, **kwargs)
    
    def generate_invoice_number(self):
        """Generate unique invoice number"""
        import random
        import string
        
        prefix = 'INV'
        year = timezone.now().year
        random_part = ''.join(random.choices(string.digits, k=6))
        
        invoice_number = f"{prefix}{year}{random_part}"
        
        # Ensure uniqueness
        while BookingInvoice.objects.filter(invoice_number=invoice_number).exists():
            random_part = ''.join(random.choices(string.digits, k=6))
            invoice_number = f"{prefix}{year}{random_part}"
        
        return invoice_number


class BookingNote(TimeStampedModel):
    """Internal notes for bookings"""
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    content = models.TextField()
    is_important = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Booking Note'
        verbose_name_plural = 'Booking Notes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note for {self.booking.booking_number} by {self.author.get_full_name()}"
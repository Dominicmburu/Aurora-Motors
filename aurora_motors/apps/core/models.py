from django.db import models
from django.utils import timezone

class TimeStampedModel(models.Model):
    """Abstract base model with timestamp fields"""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class SiteSettings(models.Model):
    """Site-wide settings"""
    
    # Company information
    company_name = models.CharField(max_length=200, default='Aurora Motors Pty Ltd')
    company_email = models.EmailField(default='info@auroramotors.com')
    company_phone = models.CharField(max_length=20, default='+61 2 1234 5678')
    company_address = models.TextField(default='123 Motor Street, Sydney, NSW 2000, Australia')
    
    # Site settings
    site_name = models.CharField(max_length=200, default='Aurora Motors')
    site_description = models.TextField(default='Premium Car Rental Service')
    site_logo = models.ImageField(upload_to='site/', blank=True, null=True)
    favicon = models.ImageField(upload_to='site/', blank=True, null=True)
    
    # Business settings
    booking_lead_time_hours = models.PositiveIntegerField(default=2)
    booking_max_duration_days = models.PositiveIntegerField(default=30)
    booking_buffer_minutes = models.PositiveIntegerField(default=30)
    
    # Email settings
    notification_email = models.EmailField(default='notifications@auroramotors.com')
    support_email = models.EmailField(default='support@auroramotors.com')
    
    # Social media
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    
    # Feature flags
    maintenance_mode = models.BooleanField(default=False)
    allow_registrations = models.BooleanField(default=True)
    require_email_verification = models.BooleanField(default=True)
    
    # Analytics
    google_analytics_id = models.CharField(max_length=50, blank=True)
    facebook_pixel_id = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'
    
    def __str__(self):
        return self.site_name
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SiteSettings.objects.exists():
            raise ValueError('Only one SiteSettings instance is allowed')
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create site settings"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
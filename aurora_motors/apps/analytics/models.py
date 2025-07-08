from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.core.models import TimeStampedModel
import json

class AnalyticsEvent(TimeStampedModel):
    """Track analytics events"""
    
    EVENT_CATEGORIES = (
        ('user', 'User Activity'),
        ('booking', 'Booking Activity'),
        ('vehicle', 'Vehicle Activity'),
        ('document', 'Document Activity'),
        ('contract', 'Contract Activity'),
        ('system', 'System Activity'),
        ('marketing', 'Marketing Activity'),
    )
    
    EVENT_ACTIONS = (
        ('view', 'View'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('click', 'Click'),
        ('download', 'Download'),
        ('search', 'Search'),
        ('filter', 'Filter'),
        ('share', 'Share'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('register', 'Register'),
        ('error', 'Error'),
    )
    
    # Event details
    category = models.CharField(max_length=50, choices=EVENT_CATEGORIES)
    action = models.CharField(max_length=50, choices=EVENT_ACTIONS)
    label = models.CharField(max_length=200, blank=True)
    value = models.IntegerField(null=True, blank=True)
    
    # User and session
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='analytics_events'
    )
    session_key = models.CharField(max_length=40, blank=True)
    
    # Related object (generic foreign key)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Request details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True)
    path = models.CharField(max_length=500, blank=True)
    
    # Additional data
    properties = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Analytics Event'
        verbose_name_plural = 'Analytics Events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'action']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['session_key', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.category}:{self.action} - {self.label}"


class Report(TimeStampedModel):
    """Saved reports"""
    
    REPORT_TYPES = (
        ('user_activity', 'User Activity'),
        ('booking_analytics', 'Booking Analytics'),
        ('vehicle_utilization', 'Vehicle Utilization'),
        ('revenue_analysis', 'Revenue Analysis'),
        ('document_compliance', 'Document Compliance'),
        ('contract_performance', 'Contract Performance'),
        ('system_performance', 'System Performance'),
        ('marketing_analysis', 'Marketing Analysis'),
    )
    
    REPORT_FORMATS = (
        ('table', 'Table'),
        ('chart', 'Chart'),
        ('dashboard', 'Dashboard'),
    )
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    
    # Report configuration
    config = models.JSONField(default=dict)
    filters = models.JSONField(default=dict)
    
    # Report data cache
    data = models.JSONField(default=dict, blank=True)
    last_generated = models.DateTimeField(null=True, blank=True)
    
    # Settings
    is_scheduled = models.BooleanField(default=False)
    schedule_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
        ],
        blank=True
    )
    
    # Access control
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='created_reports'
    )
    is_public = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(
        'accounts.CustomUser',
        blank=True,
        related_name='shared_reports'
    )
    
    class Meta:
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def generate_data(self):
        """Generate report data based on type and config"""
        from .utils import ReportGenerator
        
        generator = ReportGenerator(self)
        self.data = generator.generate()
        self.last_generated = timezone.now()
        self.save()
        
        return self.data


class Dashboard(TimeStampedModel):
    """Custom dashboards"""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Dashboard configuration
    layout = models.JSONField(default=dict)
    widgets = models.JSONField(default=list)
    
    # Access control
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='created_dashboards'
    )
    is_default = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Dashboard'
        verbose_name_plural = 'Dashboards'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Metric(TimeStampedModel):
    """System metrics tracking"""
    
    METRIC_TYPES = (
        ('counter', 'Counter'),
        ('gauge', 'Gauge'),
        ('histogram', 'Histogram'),
        ('timer', 'Timer'),
    )
    
    name = models.CharField(max_length=200)
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES)
    value = models.FloatField()
    
    # Metadata
    tags = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = 'Metric'
        verbose_name_plural = 'Metrics'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['name', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.name}: {self.value}"


class KPI(TimeStampedModel):
    """Key Performance Indicators"""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # KPI calculation
    calculation_method = models.CharField(
        max_length=50,
        choices=[
            ('sql', 'SQL Query'),
            ('python', 'Python Function'),
            ('aggregation', 'Data Aggregation'),
        ]
    )
    calculation_config = models.JSONField(default=dict)
    
    # Current value
    current_value = models.FloatField(null=True, blank=True)
    previous_value = models.FloatField(null=True, blank=True)
    target_value = models.FloatField(null=True, blank=True)
    
    # Update frequency
    update_frequency = models.CharField(
        max_length=20,
        choices=[
            ('realtime', 'Real-time'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='daily'
    )
    last_updated = models.DateTimeField(null=True, blank=True)
    
    # Display settings
    unit = models.CharField(max_length=20, blank=True)
    format_type = models.CharField(
        max_length=20,
        choices=[
            ('number', 'Number'),
            ('percentage', 'Percentage'),
            ('currency', 'Currency'),
            ('duration', 'Duration'),
        ],
        default='number'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'KPI'
        verbose_name_plural = 'KPIs'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def change_percentage(self):
        """Calculate percentage change from previous value"""
        if self.previous_value and self.current_value:
            if self.previous_value == 0:
                return 100 if self.current_value > 0 else 0
            return ((self.current_value - self.previous_value) / self.previous_value) * 100
        return 0
    
    @property
    def is_on_target(self):
        """Check if current value meets target"""
        if self.target_value and self.current_value:
            return self.current_value >= self.target_value
        return None
    
    def update_value(self):
        """Update KPI value based on calculation method"""
        from .utils import KPICalculator
        
        calculator = KPICalculator(self)
        new_value = calculator.calculate()
        
        if new_value is not None:
            self.previous_value = self.current_value
            self.current_value = new_value
            self.last_updated = timezone.now()
            self.save()
        
        return new_value
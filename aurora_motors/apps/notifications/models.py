

from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.core.models import TimeStampedModel

class NotificationTemplate(TimeStampedModel):
    """Notification template model"""
    
    TEMPLATE_TYPES = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Notification'),
    )
    
    TRIGGER_TYPES = (
        ('booking_confirmation', 'Booking Confirmation'),
        ('booking_reminder', 'Booking Reminder'),
        ('contract_signature', 'Contract Signature'),
        ('document_approval', 'Document Approval'),
        ('document_rejection', 'Document Rejection'),
        ('document_expiry', 'Document Expiry'),
        ('vehicle_pickup', 'Vehicle Pickup'),
        ('vehicle_return', 'Vehicle Return'),
        ('payment_due', 'Payment Due'),
        ('system_maintenance', 'System Maintenance'),
        ('welcome', 'Welcome Message'),
        ('password_reset', 'Password Reset'),
    )
    
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    trigger_type = models.CharField(max_length=50, choices=TRIGGER_TYPES)
    
    # Email specific fields
    subject = models.CharField(max_length=200, blank=True)
    email_body = models.TextField(blank=True)
    email_html_body = models.TextField(blank=True)
    
    # SMS specific fields
    sms_body = models.TextField(blank=True)
    
    # Push notification fields
    push_title = models.CharField(max_length=100, blank=True)
    push_body = models.TextField(blank=True)
    
    # In-app notification fields
    in_app_title = models.CharField(max_length=100, blank=True)
    in_app_body = models.TextField(blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
        ordering = ['trigger_type', 'template_type']
        unique_together = ['trigger_type', 'template_type']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def render_content(self, context=None):
        """Render template content with context variables"""
        if not context:
            context = {}
        
        rendered = {}
        
        # Render different content types
        if self.template_type == 'email':
            rendered['subject'] = self.render_text(self.subject, context)
            rendered['body'] = self.render_text(self.email_body, context)
            rendered['html_body'] = self.render_text(self.email_html_body, context)
        elif self.template_type == 'sms':
            rendered['body'] = self.render_text(self.sms_body, context)
        elif self.template_type == 'push':
            rendered['title'] = self.render_text(self.push_title, context)
            rendered['body'] = self.render_text(self.push_body, context)
        elif self.template_type == 'in_app':
            rendered['title'] = self.render_text(self.in_app_title, context)
            rendered['body'] = self.render_text(self.in_app_body, context)
        
        return rendered
    
    def render_text(self, text, context):
        """Render text with context variables"""
        if not text:
            return ''
        
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            text = text.replace(placeholder, str(value))
        
        return text


class Notification(TimeStampedModel):
    """Notification model"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    # Basic information
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    recipient = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Content
    subject = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=100, blank=True)
    body = models.TextField()
    html_body = models.TextField(blank=True)
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Scheduling
    scheduled_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Related object (generic foreign key)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional data
    context_data = models.JSONField(default=dict, blank=True)
    delivery_data = models.JSONField(default=dict, blank=True)
    
    # Retry information
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    # External tracking
    external_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['template', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.template.name} to {self.recipient.get_full_name()}"
    
    @property
    def is_overdue(self):
        """Check if notification is overdue for sending"""
        return (
            self.status == 'pending' and 
            self.scheduled_at < timezone.now()
        )
    
    @property
    def can_retry(self):
        """Check if notification can be retried"""
        return (
            self.status == 'failed' and 
            self.retry_count < self.max_retries
        )
    
    def mark_sent(self, external_id=None, delivery_data=None):
        """Mark notification as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        if external_id:
            self.external_id = external_id
        if delivery_data:
            self.delivery_data = delivery_data
        self.save()
    
    def mark_delivered(self, delivery_data=None):
        """Mark notification as delivered"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        if delivery_data:
            self.delivery_data.update(delivery_data)
        self.save()
    
    def mark_failed(self, error_message=None):
        """Mark notification as failed"""
        self.status = 'failed'
        if error_message:
            self.delivery_data['error'] = error_message
        
        # Schedule retry if possible
        if self.can_retry:
            self.retry_count += 1
            # Exponential backoff: 5 minutes, 15 minutes, 45 minutes
            delay_minutes = 5 * (3 ** (self.retry_count - 1))
            self.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
        
        self.save()
    
    def mark_read(self):
        """Mark notification as read"""
        if self.status in ['sent', 'delivered']:
            self.status = 'read'
            self.read_at = timezone.now()
            self.save()


class NotificationPreference(TimeStampedModel):
    """User notification preferences"""
    
    user = models.OneToOneField(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email preferences
    email_enabled = models.BooleanField(default=True)
    email_booking_confirmations = models.BooleanField(default=True)
    email_booking_reminders = models.BooleanField(default=True)
    email_contract_notifications = models.BooleanField(default=True)
    email_document_notifications = models.BooleanField(default=True)
    email_marketing = models.BooleanField(default=False)
    
    # SMS preferences
    sms_enabled = models.BooleanField(default=False)
    sms_booking_reminders = models.BooleanField(default=False)
    sms_urgent_notifications = models.BooleanField(default=False)
    
    # Push notification preferences
    push_enabled = models.BooleanField(default=True)
    push_booking_updates = models.BooleanField(default=True)
    push_document_updates = models.BooleanField(default=True)
    
    # In-app notification preferences
    in_app_enabled = models.BooleanField(default=True)
    in_app_all_notifications = models.BooleanField(default=True)
    
    # Frequency settings
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest'),
            ('never', 'Never'),
        ],
        default='immediate'
    )
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.get_full_name()}"
    
    def should_send_notification(self, template):
        """Check if notification should be sent based on preferences"""
        if not self.user.is_active:
            return False
        
        template_type = template.template_type
        trigger_type = template.trigger_type
        
        # Check general preferences
        if template_type == 'email' and not self.email_enabled:
            return False
        elif template_type == 'sms' and not self.sms_enabled:
            return False
        elif template_type == 'push' and not self.push_enabled:
            return False
        elif template_type == 'in_app' and not self.in_app_enabled:
            return False
        
        # Check specific trigger preferences
        if trigger_type == 'booking_confirmation' and template_type == 'email':
            return self.email_booking_confirmations
        elif trigger_type == 'booking_reminder':
            if template_type == 'email':
                return self.email_booking_reminders
            elif template_type == 'sms':
                return self.sms_booking_reminders
        elif 'contract' in trigger_type and template_type == 'email':
            return self.email_contract_notifications
        elif 'document' in trigger_type and template_type == 'email':
            return self.email_document_notifications
        
        return True
    
    def is_quiet_hours(self):
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled or not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        now = timezone.now().time()
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Same day range (e.g., 10:00 - 18:00)
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            # Overnight range (e.g., 22:00 - 06:00)
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end


class NotificationChannel(TimeStampedModel):
    """Notification delivery channels"""
    
    CHANNEL_TYPES = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('webhook', 'Webhook'),
        ('slack', 'Slack'),
    )
    
    name = models.CharField(max_length=100)
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Configuration
    config = models.JSONField(default=dict)
    
    # Rate limiting
    rate_limit_per_minute = models.PositiveIntegerField(default=60)
    rate_limit_per_hour = models.PositiveIntegerField(default=1000)
    rate_limit_per_day = models.PositiveIntegerField(default=10000)
    
    # Statistics
    total_sent = models.PositiveIntegerField(default=0)
    total_delivered = models.PositiveIntegerField(default=0)
    total_failed = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Notification Channel'
        verbose_name_plural = 'Notification Channels'
        ordering = ['channel_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"
    
    @property
    def delivery_rate(self):
        """Get delivery success rate"""
        total_attempts = self.total_sent + self.total_failed
        if total_attempts > 0:
            return (self.total_delivered / total_attempts) * 100
        return 0
    
    def increment_sent(self):
        """Increment sent counter"""
        self.total_sent += 1
        self.save(update_fields=['total_sent'])
    
    def increment_delivered(self):
        """Increment delivered counter"""
        self.total_delivered += 1
        self.save(update_fields=['total_delivered'])
    
    def increment_failed(self):
        """Increment failed counter"""
        self.total_failed += 1
        self.save(update_fields=['total_failed'])


class NotificationLog(TimeStampedModel):
    """Notification delivery log"""
    
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    # Delivery details
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20)
    response_code = models.CharField(max_length=10, blank=True)
    response_message = models.TextField(blank=True)
    
    # Timing
    sent_at = models.DateTimeField()
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Additional data
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.notification} via {self.channel} - {self.status}"


class NotificationQueue(models.Model):
    """Notification processing queue"""
    
    QUEUE_TYPES = (
        ('immediate', 'Immediate'),
        ('high', 'High Priority'),
        ('normal', 'Normal Priority'),
        ('low', 'Low Priority'),
        ('digest', 'Digest'),
    )
    
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name='queue_item'
    )
    queue_type = models.CharField(max_length=20, choices=QUEUE_TYPES, default='normal')
    priority_score = models.IntegerField(default=0)
    
    # Processing
    is_processing = models.BooleanField(default=False)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_worker = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Notification Queue Item'
        verbose_name_plural = 'Notification Queue Items'
        ordering = ['-priority_score', 'created_at']
        indexes = [
            models.Index(fields=['queue_type', 'is_processing']),
            models.Index(fields=['priority_score', 'created_at']),
        ]
    
    def __str__(self):
        return f"Queue: {self.notification}"
    
    def start_processing(self, worker_id):
        """Mark as being processed"""
        self.is_processing = True
        self.processing_started_at = timezone.now()
        self.processing_worker = worker_id
        self.save()
    
    def finish_processing(self):
        """Remove from queue after processing"""
        self.delete()
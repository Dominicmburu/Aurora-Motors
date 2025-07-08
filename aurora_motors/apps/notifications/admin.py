from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    NotificationTemplate, Notification, NotificationPreference,
    NotificationChannel, NotificationLog, NotificationQueue
)

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'template_type', 'trigger_type', 'is_active',
        'is_required', 'notification_count'
    ]
    list_filter = ['template_type', 'trigger_type', 'is_active', 'is_required']
    search_fields = ['name', 'subject', 'email_body']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'template_type', 'trigger_type', 'is_active', 'is_required')
        }),
        ('Email Template', {
            'fields': ('subject', 'email_body', 'email_html_body'),
            'classes': ('collapse',)
        }),
        ('SMS Template', {
            'fields': ('sms_body',),
            'classes': ('collapse',)
        }),
        ('Push Notification Template', {
            'fields': ('push_title', 'push_body'),
            'classes': ('collapse',)
        }),
        ('In-App Notification Template', {
            'fields': ('in_app_title', 'in_app_body'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def notification_count(self, obj):
        return obj.notifications.count()
    notification_count.short_description = 'Notifications Sent'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            notification_count=Count('notifications')
        )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'template', 'recipient', 'status', 'priority', 'scheduled_at',
        'sent_at', 'retry_count'
    ]
    list_filter = ['status', 'priority', 'template__template_type', 'created_at']
    search_fields = [
        'subject', 'body', 'recipient__email', 'recipient__first_name',
        'recipient__last_name'
    ]
    readonly_fields = [
        'sent_at', 'delivered_at', 'read_at', 'external_id',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('template', 'recipient', 'status', 'priority')
        }),
        ('Content', {
            'fields': ('subject', 'title', 'body', 'html_body')
        }),
        ('Scheduling', {
            'fields': ('scheduled_at', 'sent_at', 'delivered_at', 'read_at')
        }),
        ('Retry Information', {
            'fields': ('retry_count', 'max_retries', 'next_retry_at')
        }),
        ('Tracking', {
            'fields': ('external_id', 'delivery_data')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['retry_failed_notifications', 'mark_as_sent']
    
    def retry_failed_notifications(self, request, queryset):
        updated = 0
        for notification in queryset.filter(status='failed'):
            if notification.can_retry:
                notification.status = 'pending'
                notification.save()
                updated += 1
        self.message_user(request, f'{updated} notifications queued for retry.')
    retry_failed_notifications.short_description = 'Retry failed notifications'
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='sent',
            sent_at=timezone.now()
        )
        self.message_user(request, f'{updated} notifications marked as sent.')
    mark_as_sent.short_description = 'Mark selected notifications as sent'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'email_enabled', 'sms_enabled', 'push_enabled',
        'in_app_enabled', 'digest_frequency'
    ]
    list_filter = [
        'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled',
        'digest_frequency'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Preferences', {
            'fields': (
                'email_enabled', 'email_booking_confirmations',
                'email_booking_reminders', 'email_contract_notifications',
                'email_document_notifications', 'email_marketing'
            )
        }),
        ('SMS Preferences', {
            'fields': ('sms_enabled', 'sms_booking_reminders', 'sms_urgent_notifications')
        }),
        ('Push Notification Preferences', {
            'fields': ('push_enabled', 'push_booking_updates', 'push_document_updates')
        }),
        ('In-App Notification Preferences', {
            'fields': ('in_app_enabled', 'in_app_all_notifications')
        }),
        ('General Settings', {
            'fields': ('digest_frequency', 'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end')
        }),
    )


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'channel_type', 'is_active', 'is_default',
        'total_sent', 'total_delivered', 'delivery_rate_display'
    ]
    list_filter = ['channel_type', 'is_active', 'is_default']
    search_fields = ['name']
    readonly_fields = [
        'total_sent', 'total_delivered', 'total_failed',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Channel Information', {
            'fields': ('name', 'channel_type', 'is_active', 'is_default')
        }),
        ('Rate Limiting', {
            'fields': ('rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day')
        }),
        ('Configuration', {
            'fields': ('config',)
        }),
        ('Statistics', {
            'fields': ('total_sent', 'total_delivered', 'total_failed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def delivery_rate_display(self, obj):
        rate = obj.delivery_rate
        if rate >= 95:
            color = 'green'
        elif rate >= 85:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    delivery_rate_display.short_description = 'Delivery Rate'


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'notification', 'channel', 'status', 'attempt_number',
        'sent_at', 'delivered_at'
    ]
    list_filter = ['status', 'channel', 'sent_at']
    search_fields = ['notification__subject', 'response_message']
    readonly_fields = ['sent_at', 'delivered_at']
    date_hierarchy = 'sent_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    list_display = [
        'notification', 'queue_type', 'priority_score', 'is_processing',
        'processing_started_at', 'created_at'
    ]
    list_filter = ['queue_type', 'is_processing', 'created_at']
    search_fields = ['notification__subject']
    readonly_fields = ['processing_started_at', 'created_at']
    
    actions = ['reset_processing_status']
    
    def reset_processing_status(self, request, queryset):
        updated = queryset.update(
            is_processing=False,
            processing_started_at=None,
            processing_worker=''
        )
        self.message_user(request, f'{updated} queue items reset.')
    reset_processing_status.short_description = 'Reset processing status'
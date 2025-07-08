from rest_framework import serializers
from .models import (
    Notification, NotificationTemplate, NotificationPreference,
    NotificationChannel
)

class NotificationSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.template_type', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'template_name', 'template_type', 'subject', 'title',
            'body', 'status', 'priority', 'scheduled_at', 'sent_at',
            'delivered_at', 'read_at', 'is_overdue', 'created_at'
        ]

class NotificationTemplateSerializer(serializers.ModelSerializer):
    notification_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'template_type', 'trigger_type', 'is_active',
            'is_required', 'notification_count'
        ]

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'email_booking_confirmations', 'email_booking_reminders',
            'email_contract_notifications', 'email_document_notifications',
            'email_marketing', 'sms_enabled', 'sms_booking_reminders',
            'sms_urgent_notifications', 'push_enabled', 'push_booking_updates',
            'push_document_updates', 'in_app_enabled', 'in_app_all_notifications',
            'digest_frequency', 'quiet_hours_enabled', 'quiet_hours_start',
            'quiet_hours_end'
        ]

class NotificationChannelSerializer(serializers.ModelSerializer):
    delivery_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = NotificationChannel
        fields = [
            'id', 'name', 'channel_type', 'is_active', 'is_default',
            'total_sent', 'total_delivered', 'total_failed', 'delivery_rate'
        ]
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
import requests
import json
import logging

from .models import (
    Notification, NotificationTemplate, NotificationQueue,
    NotificationChannel, NotificationLog, NotificationPreference
)

logger = logging.getLogger(__name__)

@shared_task
def create_notification(template_id, recipient_id, context=None, scheduled_at=None, priority='normal'):
    """Create a notification from template"""
    
    try:
        template = NotificationTemplate.objects.get(id=template_id)
        from apps.accounts.models import CustomUser
        recipient = CustomUser.objects.get(id=recipient_id)
        
        # Check user preferences
        preferences, _ = NotificationPreference.objects.get_or_create(user=recipient)
        if not preferences.should_send_notification(template):
            return f"Notification skipped due to user preferences: {template.name}"
        
        # Set default context
        if not context:
            context = {}
        
        # Add common context variables
        context.update({
            'user_name': recipient.get_full_name(),
            'user_email': recipient.email,
            'company_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://auroramotors.com',
        })
        
        # Render content
        rendered_content = template.render_content(context)
        
        # Create notification
        notification = Notification.objects.create(
            template=template,
            recipient=recipient,
            subject=rendered_content.get('subject', ''),
            title=rendered_content.get('title', ''),
            body=rendered_content.get('body', ''),
            html_body=rendered_content.get('html_body', ''),
            priority=priority,
            scheduled_at=timezone.now() if not scheduled_at else scheduled_at,
            context_data=context
        )
        
        # Add to queue
        queue_type = 'immediate' if priority == 'urgent' else 'normal'
        priority_score = {
            'urgent': 100,
            'high': 75,
            'normal': 50,
            'low': 25
        }.get(priority, 50)
        
        NotificationQueue.objects.create(
            notification=notification,
            queue_type=queue_type,
            priority_score=priority_score
        )
        
        return f"Notification created: {notification.id}"
        
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return f"Failed to create notification: {e}"


@shared_task
def process_notification_queue():
    """Process pending notifications in queue"""
    
    # Get pending notifications
    queue_items = NotificationQueue.objects.filter(
        is_processing=False,
        notification__scheduled_at__lte=timezone.now()
    ).select_related('notification', 'notification__template').order_by(
        '-priority_score', 'created_at'
    )[:50]  # Process 50 at a time
    
    processed_count = 0
    
    for queue_item in queue_items:
        try:
            # Mark as processing
            queue_item.start_processing('celery_worker')
            
            notification = queue_item.notification
            
            # Send notification
            success = send_notification(notification)
            
            if success:
                # Remove from queue
                queue_item.finish_processing()
                processed_count += 1
            else:
                # Reset processing status for retry
                queue_item.is_processing = False
                queue_item.save()
                
        except Exception as e:
            logger.error(f"Failed to process notification {queue_item.notification.id}: {e}")
            # Reset processing status
            queue_item.is_processing = False
            queue_item.save()
    
    return f"Processed {processed_count} notifications"


def send_notification(notification):
    """Send a notification using appropriate channel"""
    
    template_type = notification.template.template_type
    
    try:
        # Get appropriate channel
        channel = NotificationChannel.objects.filter(
            channel_type=template_type,
            is_active=True
        ).first()
        
        if not channel:
            logger.error(f"No active channel found for type: {template_type}")
            notification.mark_failed("No active channel available")
            return False
        
        # Send based on channel type
        if template_type == 'email':
            return send_email_notification(notification, channel)
        elif template_type == 'sms':
            return send_sms_notification(notification, channel)
        elif template_type == 'push':
            return send_push_notification(notification, channel)
        elif template_type == 'in_app':
            return send_in_app_notification(notification, channel)
        else:
            logger.error(f"Unknown template type: {template_type}")
            notification.mark_failed("Unknown template type")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send notification {notification.id}: {e}")
        notification.mark_failed(str(e))
        return False


def send_email_notification(notification, channel):
    """Send email notification"""
    
    try:
        # Use Django's send_mail
        send_mail(
            subject=notification.subject,
            message=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient.email],
            html_message=notification.html_body if notification.html_body else None,
            fail_silently=False,
        )
        
        # Mark as sent
        notification.mark_sent()
        channel.increment_sent()
        
        # Log delivery
        NotificationLog.objects.create(
            notification=notification,
            channel=channel,
            status='sent',
            sent_at=timezone.now()
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email notification {notification.id}: {e}")
        notification.mark_failed(str(e))
        channel.increment_failed()
        return False


def send_sms_notification(notification, channel):
    """Send SMS notification"""
    
    # This is a placeholder - implement with your SMS provider
    # Example with Twilio or similar service
    
    try:
        config = channel.config
        api_key = config.get('api_key')
        api_secret = config.get('api_secret')
        sender_id = config.get('sender_id', 'Aurora Motors')
        
        # Implement SMS sending logic here
        # This is just an example structure
        
        # Mark as sent (placeholder)
        notification.mark_sent()
        channel.increment_sent()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send SMS notification {notification.id}: {e}")
        notification.mark_failed(str(e))
        channel.increment_failed()
        return False


def send_push_notification(notification, channel):
    """Send push notification"""
    
    # This is a placeholder - implement with Firebase Cloud Messaging or similar
    
    try:
        # Implement push notification logic here
        
        # Mark as sent (placeholder)
        notification.mark_sent()
        channel.increment_sent()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send push notification {notification.id}: {e}")
        notification.mark_failed(str(e))
        channel.increment_failed()
        return False


def send_in_app_notification(notification, channel):
    """Send in-app notification"""
    
    try:
        # In-app notifications are just stored in the database
        # They will be displayed when the user logs in
        
        notification.mark_sent()
        channel.increment_sent()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send in-app notification {notification.id}: {e}")
        notification.mark_failed(str(e))
        channel.increment_failed()
        return False


@shared_task
def send_booking_confirmation(booking_id):
    """Send booking confirmation notification"""
    
    try:
        from apps.bookings.models import Booking
        booking = Booking.objects.get(id=booking_id)
        
        template = NotificationTemplate.objects.get(
            trigger_type='booking_confirmation',
            template_type='email',
            is_active=True
        )
        
        context = {
            'booking_number': booking.booking_number,
            'vehicle_name': str(booking.vehicle),
            'start_date': booking.start_date.strftime('%Y-%m-%d %H:%M'),
            'end_date': booking.end_date.strftime('%Y-%m-%d %H:%M'),
            'total_amount': booking.total_amount,
            'pickup_location': booking.pickup_location,
            'return_location': booking.return_location,
        }
        
        return create_notification(
            template_id=template.id,
            recipient_id=booking.user.id,
            context=context,
            priority='high'
        )
        
    except Exception as e:
        logger.error(f"Failed to send booking confirmation for booking {booking_id}: {e}")
        return f"Failed: {e}"


@shared_task
def send_booking_reminder(booking_id):
    """Send booking reminder notification"""
    
    try:
        from apps.bookings.models import Booking
        booking = Booking.objects.get(id=booking_id)
        
        # Only send if booking is confirmed and starts within 24 hours
        if booking.status != 'confirmed':
            return "Booking not confirmed"
        
        time_until_pickup = booking.start_date - timezone.now()
        if time_until_pickup.total_seconds() > 86400:  # 24 hours
            return "Too early for reminder"
        
        template = NotificationTemplate.objects.get(
            trigger_type='booking_reminder',
            template_type='email',
            is_active=True
        )
        
        context = {
            'booking_number': booking.booking_number,
            'vehicle_name': str(booking.vehicle),
            'start_date': booking.start_date.strftime('%Y-%m-%d %H:%M'),
            'pickup_location': booking.pickup_location,
            'hours_until_pickup': int(time_until_pickup.total_seconds() // 3600),
        }
        
        return create_notification(
            template_id=template.id,
            recipient_id=booking.user.id,
            context=context,
            priority='high'
        )
        
    except Exception as e:
        logger.error(f"Failed to send booking reminder for booking {booking_id}: {e}")
        return f"Failed: {e}"


@shared_task
def send_contract_for_signature(contract_id):
    """Send contract for signature notification"""
    
    try:
        from apps.contracts.models import Contract
        contract = Contract.objects.get(id=contract_id)
        
        template = NotificationTemplate.objects.get(
            trigger_type='contract_signature',
            template_type='email',
            is_active=True
        )
        
        context = {
            'contract_title': contract.title,
            'booking_number': contract.booking.booking_number,
            'signing_url': contract.get_signing_url(),
            'expires_at': contract.expires_at.strftime('%Y-%m-%d %H:%M') if contract.expires_at else 'N/A',
        }
        
        return create_notification(
            template_id=template.id,
            recipient_id=contract.user.id,
            context=context,
            priority='high'
        )
        
    except Exception as e:
        logger.error(f"Failed to send contract signature notification for contract {contract_id}: {e}")
        return f"Failed: {e}"


@shared_task
def send_contract_signed_confirmation(contract_id):
    """Send contract signed confirmation notification"""
    
    try:
        from apps.contracts.models import Contract
        contract = Contract.objects.get(id=contract_id)
        
        template = NotificationTemplate.objects.get(
            trigger_type='contract_signature',
            template_type='email',
            is_active=True
        )
        
        context = {
            'contract_title': contract.title,
            'booking_number': contract.booking.booking_number,
            'signed_date': contract.signed_date.strftime('%Y-%m-%d %H:%M'),
            'download_url': contract.get_absolute_url(),
        }
        
        return create_notification(
            template_id=template.id,
            recipient_id=contract.user.id,
            context=context,
            priority='normal'
        )
        
    except Exception as e:
        logger.error(f"Failed to send contract signed confirmation for contract {contract_id}: {e}")
        return f"Failed: {e}"


@shared_task
def send_document_approval(document_id):
    """Send document approval notification"""
    
    try:
        from apps.documents.models import Document
        document = Document.objects.get(id=document_id)
        
        template = NotificationTemplate.objects.get(
            trigger_type='document_approval',
            template_type='email',
            is_active=True
        )
        
        context = {
            'document_name': document.name,
            'document_type': document.get_document_type_display(),
            'approved_date': document.verification_date.strftime('%Y-%m-%d %H:%M'),
        }
        
        return create_notification(
            template_id=template.id,
            recipient_id=document.user.id,
            context=context,
            priority='normal'
        )
        
    except Exception as e:
        logger.error(f"Failed to send document approval notification for document {document_id}: {e}")
        return f"Failed: {e}"


@shared_task
def send_document_rejection(document_id):
    """Send document rejection notification"""
    
    try:
        from apps.documents.models import Document
        document = Document.objects.get(id=document_id)
        
        template = NotificationTemplate.objects.get(
            trigger_type='document_rejection',
            template_type='email',
            is_active=True
        )
        
        context = {
            'document_name': document.name,
            'document_type': document.get_document_type_display(),
            'rejection_reason': document.rejection_reason,
            'resubmit_url': document.get_absolute_url(),
        }
        
        return create_notification(
            template_id=template.id,
            recipient_id=document.user.id,
            context=context,
            priority='high'
        )
        
    except Exception as e:
        logger.error(f"Failed to send document rejection notification for document {document_id}: {e}")
        return f"Failed: {e}"


@shared_task
def send_test_notification(template_id, test_email, context=None):
    """Send test notification to specified email"""
    
    try:
        template = NotificationTemplate.objects.get(id=template_id)
        
        if not context:
            context = {}
        
        # Render content
        rendered_content = template.render_content(context)
        
        if template.template_type == 'email':
            send_mail(
                subject=f"[TEST] {rendered_content.get('subject', '')}",
                message=rendered_content.get('body', ''),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[test_email],
                html_message=rendered_content.get('html_body', '') if rendered_content.get('html_body') else None,
                fail_silently=False,
            )
            
            return f"Test email sent to {test_email}"
        else:
            return f"Test sending not supported for {template.template_type} templates"
            
    except Exception as e:
        logger.error(f"Failed to send test notification: {e}")
        return f"Failed: {e}"


@shared_task
def send_booking_reminders():
    """Send booking reminders for upcoming rentals"""
    
    # Get bookings starting in the next 24 hours
    reminder_time = timezone.now() + timezone.timedelta(hours=24)
    
    from apps.bookings.models import Booking
    upcoming_bookings = Booking.objects.filter(
        status='confirmed',
        start_date__lte=reminder_time,
        start_date__gt=timezone.now()
    )
    
    sent_count = 0
    for booking in upcoming_bookings:
        # Check if reminder already sent
        existing_notification = Notification.objects.filter(
            recipient=booking.user,
            template__trigger_type='booking_reminder',
            context_data__booking_id=booking.id
        ).exists()
        
        if not existing_notification:
            send_booking_reminder.delay(booking.id)
            sent_count += 1
    
    return f"Queued {sent_count} booking reminders"


@shared_task
def cleanup_old_notifications():
    """Clean up old notifications"""
    
    # Delete notifications older than 90 days
    cutoff_date = timezone.now() - timezone.timedelta(days=90)
    
    deleted_count = Notification.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['read', 'delivered', 'failed']
    ).delete()[0]
    
    # Delete old notification logs
    log_deleted_count = NotificationLog.objects.filter(
        sent_at__lt=cutoff_date
    ).delete()[0]
    
    return f"Deleted {deleted_count} notifications and {log_deleted_count} logs"


@shared_task
def retry_failed_notifications():
    """Retry failed notifications that can be retried"""
    
    failed_notifications = Notification.objects.filter(
        status='failed',
        retry_count__lt=models.F('max_retries'),
        next_retry_at__lte=timezone.now()
    )
    
    retried_count = 0
    for notification in failed_notifications:
        # Reset status and add back to queue
        notification.status = 'pending'
        notification.save()
        
        NotificationQueue.objects.create(
            notification=notification,
            queue_type='normal',
            priority_score=25  # Lower priority for retries
        )
        
        retried_count += 1
    
    return f"Retried {retried_count} failed notifications"


@shared_task
def generate_notification_report():
    """Generate daily notification statistics report"""
    
    from django.db.models import Count
    from datetime import timedelta
    
    # Get yesterday's data
    yesterday = timezone.now().date() - timedelta(days=1)
    
    notifications = Notification.objects.filter(
        created_at__date=yesterday
    )
    
    stats = {
        'date': yesterday.isoformat(),
        'total_notifications': notifications.count(),
        'sent_notifications': notifications.filter(status__in=['sent', 'delivered', 'read']).count(),
        'failed_notifications': notifications.filter(status='failed').count(),
        'pending_notifications': notifications.filter(status='pending').count(),
        'by_template_type': {},
        'by_trigger_type': {},
    }
    
    # Notifications by template type
    type_data = notifications.values(
        'template__template_type'
    ).annotate(count=Count('id'))
    
    for item in type_data:
        stats['by_template_type'][item['template__template_type']] = item['count']
    
    # Notifications by trigger type
    trigger_data = notifications.values(
        'template__trigger_type'
    ).annotate(count=Count('id'))
    
    for item in trigger_data:
        stats['by_trigger_type'][item['template__trigger_type']] = item['count']
    
    # Send report to admin
    from apps.accounts.models import CustomUser
    admin_emails = [
        user.email for user in 
        CustomUser.objects.filter(is_staff=True, is_active=True)
    ]
    
    if admin_emails and stats['total_notifications'] > 0:
        subject = f"Daily Notification Report - {yesterday}"
        message = render_to_string('notifications/emails/daily_report.txt', {
            'stats': stats,
            'date': yesterday,
        })
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=True,
        )
    
    return f"Generated notification report for {yesterday}: {stats}"
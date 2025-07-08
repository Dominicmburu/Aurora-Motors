from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Booking

@shared_task
def cleanup_expired_bookings():
    """Mark expired bookings as cancelled"""
    
    expired_bookings = Booking.objects.filter(
        status='pending',
        created_at__lt=timezone.now() - timezone.timedelta(hours=24)
    )
    
    updated_count = expired_bookings.update(
        status='cancelled',
        cancellation_reason='expired'
    )
    
    return f"Cancelled {updated_count} expired bookings"

@shared_task
def send_booking_reminders():
    """Send booking reminders"""
    
    upcoming_bookings = Booking.objects.filter(
        status='confirmed',
        start_date__gte=timezone.now(),
        start_date__lte=timezone.now() + timezone.timedelta(hours=24)
    )
    
    sent_count = 0
    for booking in upcoming_bookings:
        try:
            send_mail(
                subject=f'Booking Reminder - {booking.booking_number}',
                message=f'Your booking starts tomorrow at {booking.start_date}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.user.email],
                fail_silently=False,
            )
            sent_count += 1
        except Exception as e:
            print(f"Failed to send reminder for booking {booking.booking_number}: {e}")
    
    return f"Sent {sent_count} booking reminders"
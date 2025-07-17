from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from .models import UserProfile, Booking, Review
from .utils import send_booking_confirmation_email

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when user is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()

@receiver(post_save, sender=Booking)
def booking_status_changed(sender, instance, created, **kwargs):
    """Handle booking status changes"""
    if created:
        # Send confirmation email for new bookings
        send_booking_confirmation_email(instance)
    else:
        # Handle status changes
        if instance.status == 'confirmed':
            # Send confirmation email
            send_booking_confirmation_email(instance)
        elif instance.status == 'cancelled':
            # Send cancellation email
            pass

@receiver(post_save, sender=Review)
def review_created(sender, instance, created, **kwargs):
    """Handle new review creation"""
    if created:
        # Send thank you email
        pass
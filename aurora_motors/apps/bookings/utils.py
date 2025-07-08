from django.utils import timezone
from decimal import Decimal

def calculate_booking_cost(vehicle, start_date, end_date):
    """Calculate total booking cost"""
    
    duration = (end_date - start_date).days
    if duration == 0:
        duration = 1
    
    return vehicle.get_rate_for_duration(duration)

def check_vehicle_availability(vehicle, start_date, end_date, exclude_booking=None):
    """Check if vehicle is available for given period"""
    
    from .models import Booking
    
    overlapping_bookings = Booking.objects.filter(
        vehicle=vehicle,
        status__in=['confirmed', 'active'],
        start_date__lt=end_date,
        end_date__gt=start_date
    )
    
    if exclude_booking:
        overlapping_bookings = overlapping_bookings.exclude(pk=exclude_booking.pk)
    
    return not overlapping_bookings.exists()

def generate_booking_number():
    """Generate unique booking number"""
    import random
    import string
    
    prefix = 'BK'
    year = timezone.now().year
    random_part = ''.join(random.choices(string.digits, k=6))
    
    return f"{prefix}{year}{random_part}"
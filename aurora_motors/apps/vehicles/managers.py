from django.db import models
from django.utils import timezone

class VehicleQuerySet(models.QuerySet):
    """Custom queryset for Vehicle model"""
    
    def available(self):
        """Get available vehicles"""
        return self.filter(status='available', is_active=True)
    
    def featured(self):
        """Get featured vehicles"""
        return self.filter(is_featured=True, is_active=True)
    
    def by_category(self, category):
        """Filter by category"""
        return self.filter(category=category)
    
    def by_brand(self, brand):
        """Filter by brand"""
        return self.filter(brand=brand)
    
    def by_transmission(self, transmission):
        """Filter by transmission"""
        return self.filter(transmission=transmission)
    
    def by_fuel_type(self, fuel_type):
        """Filter by fuel type"""
        return self.filter(fuel_type=fuel_type)
    
    def by_price_range(self, min_price, max_price):
        """Filter by price range"""
        queryset = self
        if min_price:
            queryset = queryset.filter(daily_rate__gte=min_price)
        if max_price:
            queryset = queryset.filter(daily_rate__lte=max_price)
        return queryset
    
    def by_seats(self, min_seats, max_seats=None):
        """Filter by number of seats"""
        queryset = self.filter(seats__gte=min_seats)
        if max_seats:
            queryset = queryset.filter(seats__lte=max_seats)
        return queryset
    
    def available_for_period(self, start_date, end_date):
        """Get vehicles available for a specific period"""
        from apps.bookings.models import Booking
        
        # Get vehicles with overlapping bookings
        overlapping_bookings = Booking.objects.filter(
            status__in=['confirmed', 'active'],
            start_date__lt=end_date,
            end_date__gt=start_date
        ).values_list('vehicle_id', flat=True)
        
        return self.available().exclude(id__in=overlapping_bookings)
    
    def needs_maintenance(self):
        """Get vehicles that need maintenance"""
        today = timezone.now().date()
        return self.filter(
            models.Q(next_service_date__lte=today) |
            models.Q(next_service_mileage__lte=models.F('mileage'))
        )
    
    def insurance_expiring(self, days=30):
        """Get vehicles with insurance expiring within specified days"""
        cutoff_date = timezone.now().date() + timezone.timedelta(days=days)
        return self.filter(
            insurance_expiry__lte=cutoff_date,
            insurance_expiry__gte=timezone.now().date()
        )


class VehicleManager(models.Manager):
    """Custom manager for Vehicle model"""
    
    def get_queryset(self):
        return VehicleQuerySet(self.model, using=self._db)
    
    def available(self):
        return self.get_queryset().available()
    
    def featured(self):
        return self.get_queryset().featured()
    
    def by_category(self, category):
        return self.get_queryset().by_category(category)
    
    def by_brand(self, brand):
        return self.get_queryset().by_brand(brand)
    
    def available_for_period(self, start_date, end_date):
        return self.get_queryset().available_for_period(start_date, end_date)
    
    def needs_maintenance(self):
        return self.get_queryset().needs_maintenance()
    
    def insurance_expiring(self, days=30):
        return self.get_queryset().insurance_expiring(days)


# Add manager to Vehicle model
from apps.vehicles.models import Vehicle
Vehicle.add_to_class('objects', VehicleManager())
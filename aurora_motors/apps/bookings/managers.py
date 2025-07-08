from django.db import models
from django.utils import timezone

class BookingQuerySet(models.QuerySet):
    """Custom queryset for Booking model"""
    
    def pending(self):
        """Get pending bookings"""
        return self.filter(status='pending')
    
    def confirmed(self):
        """Get confirmed bookings"""
        return self.filter(status='confirmed')
    
    def active(self):
        """Get active bookings"""
        return self.filter(status='active')
    
    def completed(self):
        """Get completed bookings"""
        return self.filter(status='completed')
    
    def cancelled(self):
        """Get cancelled bookings"""
        return self.filter(status='cancelled')
    
    def for_user(self, user):
        """Get bookings for a specific user"""
        return self.filter(user=user)
    
    def for_vehicle(self, vehicle):
        """Get bookings for a specific vehicle"""
        return self.filter(vehicle=vehicle)
    
    def upcoming(self):
        """Get upcoming bookings"""
        return self.filter(
            status__in=['confirmed', 'active'],
            start_date__gt=timezone.now()
        )
    
    def current(self):
        """Get current active bookings"""
        now = timezone.now()
        return self.filter(
            status='active',
            start_date__lte=now,
            end_date__gte=now
        )
    
    def overdue(self):
        """Get overdue bookings"""
        return self.filter(
            status__in=['confirmed', 'active'],
            end_date__lt=timezone.now()
        )
    
    def today(self):
        """Get bookings for today"""
        today = timezone.now().date()
        return self.filter(
            start_date__date=today
        )
    
    def this_week(self):
        """Get bookings for this week"""
        today = timezone.now().date()
        start_week = today - timezone.timedelta(days=today.weekday())
        end_week = start_week + timezone.timedelta(days=6)
        return self.filter(
            start_date__date__range=[start_week, end_week]
        )
    
    def this_month(self):
        """Get bookings for this month"""
        today = timezone.now().date()
        return self.filter(
            start_date__year=today.year,
            start_date__month=today.month
        )
    
    def by_date_range(self, start_date, end_date):
        """Get bookings within date range"""
        return self.filter(
            start_date__date__range=[start_date, end_date]
        )
    
    def with_vehicle_conflicts(self):
        """Get bookings with potential vehicle conflicts"""
        return self.filter(
            status__in=['confirmed', 'active']
        ).extra(
            where=["""
                EXISTS (
                    SELECT 1 FROM bookings_booking b2 
                    WHERE b2.vehicle_id = bookings_booking.vehicle_id 
                    AND b2.id != bookings_booking.id
                    AND b2.status IN ('confirmed', 'active')
                    AND b2.start_date < bookings_booking.end_date
                    AND b2.end_date > bookings_booking.start_date
                )
            """]
        )


class BookingManager(models.Manager):
    """Custom manager for Booking model"""
    
    def get_queryset(self):
        return BookingQuerySet(self.model, using=self._db)
    
    def pending(self):
        return self.get_queryset().pending()
    
    def confirmed(self):
        return self.get_queryset().confirmed()
    
    def active(self):
        return self.get_queryset().active()
    
    def completed(self):
        return self.get_queryset().completed()
    
    def cancelled(self):
        return self.get_queryset().cancelled()
    
    def upcoming(self):
        return self.get_queryset().upcoming()
    
    def current(self):
        return self.get_queryset().current()
    
    def overdue(self):
        return self.get_queryset().overdue()
    
    def for_dashboard(self):
        """Get booking statistics for dashboard"""
        return {
            'total': self.count(),
            'pending': self.pending().count(),
            'confirmed': self.confirmed().count(),
            'active': self.active().count(),
            'completed': self.completed().count(),
            'cancelled': self.cancelled().count(),
            'overdue': self.overdue().count(),
        }


# Add manager to Booking model
from apps.bookings.models import Booking
Booking.add_to_class('objects', BookingManager())
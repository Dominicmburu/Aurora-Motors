from celery import shared_task
from django.utils import timezone
from .models import KPI, Metric, AnalyticsEvent
from .utils import KPICalculator

@shared_task
def update_kpis():
    """Update all active KPIs"""
    
    kpis = KPI.objects.filter(is_active=True)
    updated_count = 0
    
    for kpi in kpis:
        try:
            old_value = kpi.current_value
            new_value = kpi.update_value()
            
            if new_value is not None:
                updated_count += 1
                
                # Log the update as a metric
                Metric.objects.create(
                    name=f"kpi_{kpi.name.lower().replace(' ', '_')}",
                    metric_type='gauge',
                    value=new_value,
                    tags={'kpi_id': kpi.id}
                )
        
        except Exception as e:
            print(f"Failed to update KPI {kpi.name}: {e}")
    
    return f"Updated {updated_count} KPIs"

@shared_task
def cleanup_old_analytics_events():
    """Clean up old analytics events"""
    
    # Delete events older than 90 days
    cutoff_date = timezone.now() - timezone.timedelta(days=90)
    
    deleted_count = AnalyticsEvent.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    return f"Deleted {deleted_count} old analytics events"

@shared_task
def generate_daily_metrics():
    """Generate daily system metrics"""
    
    from apps.bookings.models import Booking
    from apps.accounts.models import CustomUser
    from apps.vehicles.models import Vehicle
    
    today = timezone.now().date()
    
    # Daily booking metrics
    daily_bookings = Booking.objects.filter(created_at__date=today).count()
    Metric.objects.create(
        name='daily_bookings',
        metric_type='counter',
        value=daily_bookings,
        tags={'date': today.isoformat()}
    )
    
    # Daily revenue
    daily_revenue = Booking.objects.filter(
        created_at__date=today,
        status__in=['confirmed', 'active', 'completed']
    ).aggregate(total=models.Sum('total_amount'))['total'] or 0
    
    Metric.objects.create(
        name='daily_revenue',
        metric_type='gauge',
        value=float(daily_revenue),
        tags={'date': today.isoformat()}
    )
    
    # Active users
    active_users = CustomUser.objects.filter(
        last_login__date=today
    ).count()
    
    Metric.objects.create(
        name='daily_active_users',
        metric_type='gauge',
        value=active_users,
        tags={'date': today.isoformat()}
    )
    
    return f"Generated daily metrics for {today}"
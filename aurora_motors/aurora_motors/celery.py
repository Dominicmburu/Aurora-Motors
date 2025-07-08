import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aurora_motors.settings.development')

app = Celery('aurora_motors')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery beat schedule
app.conf.beat_schedule = {
    'send-booking-reminders': {
        'task': 'apps.notifications.tasks.send_booking_reminders',
        'schedule': 300.0,  # Run every 5 minutes
    },
    'cleanup-expired-bookings': {
        'task': 'apps.bookings.tasks.cleanup_expired_bookings',
        'schedule': 3600.0,  # Run every hour
    },
    'generate-daily-reports': {
        'task': 'apps.analytics.tasks.generate_daily_reports',
        'schedule': 86400.0,  # Run every day
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
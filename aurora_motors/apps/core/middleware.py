from django.http import HttpResponse
from django.template import loader
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from .models import SiteSettings

class MaintenanceModeMiddleware(MiddlewareMixin):
    """Middleware to handle maintenance mode"""
    
    def process_request(self, request):
        settings = SiteSettings.get_settings()
        
        if settings.maintenance_mode:
            # Allow staff and admin users
            if request.user.is_authenticated and (
                request.user.is_staff or request.user.is_superuser
            ):
                return None
            
            # Allow access to admin and maintenance pages
            if request.path.startswith('/admin/') or request.path.startswith('/maintenance/'):
                return None
            
            # Show maintenance page
            template = loader.get_template('pages/maintenance.html')
            return HttpResponse(template.render({'settings': settings}, request), status=503)
        
        return None

class TimezoneMiddleware(MiddlewareMixin):
    """Middleware to handle user timezones"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # You can add user timezone preference here
            # For now, we'll use the default timezone
            pass
        return None
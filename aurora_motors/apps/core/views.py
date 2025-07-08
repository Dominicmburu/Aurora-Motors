from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import Http404
from .models import SiteSettings

class HomeView(TemplateView):
    """Home page view"""
    
    template_name = 'pages/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add featured vehicles
        from apps.vehicles.models import Vehicle
        context['featured_vehicles'] = Vehicle.objects.filter(
            is_featured=True,
            is_active=True
        )[:6]
        
        # Add testimonials/reviews
        from apps.vehicles.models import VehicleReview
        context['featured_reviews'] = VehicleReview.objects.filter(
            is_featured=True,
            is_approved=True
        )[:3]
        
        return context

def custom_404(request, exception):
    """Custom 404 error page"""
    return render(request, 'errors/404.html', status=404)

def custom_500(request):
    """Custom 500 error page"""
    return render(request, 'errors/500.html', status=500)

def custom_403(request, exception):
    """Custom 403 error page"""
    return render(request, 'errors/403.html', status=403)

class MaintenanceView(TemplateView):
    """Maintenance mode page"""
    
    template_name = 'pages/maintenance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = SiteSettings.get_settings()
        return context
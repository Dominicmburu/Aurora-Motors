from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.urls import reverse_lazy
from django.db.models import Q, Avg, Count, Prefetch
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json

from .models import (
    Vehicle, VehicleCategory, VehicleBrand, VehicleImage, 
    VehicleReview, VehicleMaintenanceRecord, VehicleFeature
)
from .forms import (
    VehicleForm, VehicleImageForm, VehicleReviewForm,
    VehicleMaintenanceForm, VehicleSearchForm, VehicleAvailabilityForm
)
from .filters import VehicleFilter, AvailabilityFilter
from apps.accounts.permissions import StaffRequiredMixin, CustomerRequiredMixin
from apps.bookings.models import Booking


class VehicleListView(ListView):
    """Vehicle listing view"""
    
    model = Vehicle
    template_name = 'vehicles/vehicle_list.html'
    context_object_name = 'vehicles'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Vehicle.objects.filter(is_active=True).select_related(
            'brand', 'category'
        ).prefetch_related('images')
        
        # Apply filters
        self.filterset = VehicleFilter(
            self.request.GET, 
            queryset=queryset
        )
        
        return self.filterset.qs.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        context['categories'] = VehicleCategory.objects.filter(is_active=True)
        context['brands'] = VehicleBrand.objects.filter(is_active=True)
        context['search_form'] = VehicleSearchForm()
        
        # Add statistics
        context['total_vehicles'] = self.get_queryset().count()
        context['featured_vehicles'] = Vehicle.objects.featured()[:4]
        
        return context


class VehicleDetailView(DetailView):
    """Vehicle detail view"""
    
    model = Vehicle
    template_name = 'vehicles/vehicle_detail.html'
    context_object_name = 'vehicle'
    
    def get_queryset(self):
        return Vehicle.objects.select_related(
            'brand', 'category'
        ).prefetch_related(
            'images',
            'features',
            Prefetch('reviews', queryset=VehicleReview.objects.filter(is_approved=True))
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle = self.object
        
        # Get reviews statistics
        reviews = vehicle.reviews.filter(is_approved=True)
        context['reviews'] = reviews[:5]  # Show first 5 reviews
        context['total_reviews'] = reviews.count()
        context['average_rating'] = reviews.aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0
        
        # Get detailed rating averages
        context['rating_breakdown'] = {
            'cleanliness': reviews.aggregate(avg=Avg('cleanliness_rating'))['avg'] or 0,
            'comfort': reviews.aggregate(avg=Avg('comfort_rating'))['avg'] or 0,
            'performance': reviews.aggregate(avg=Avg('performance_rating'))['avg'] or 0,
        }
        
        # Check availability form
        context['availability_form'] = VehicleAvailabilityForm()
        
        # Similar vehicles
        context['similar_vehicles'] = Vehicle.objects.filter(
            category=vehicle.category,
            is_active=True
        ).exclude(id=vehicle.id)[:4]
        
        # Check if user can review (has completed booking)
        if self.request.user.is_authenticated:
            can_review = Booking.objects.filter(
                user=self.request.user,
                vehicle=vehicle,
                status='completed'
            ).exclude(
                review__isnull=False
            ).exists()
            context['can_review'] = can_review
        
        return context


class VehicleSearchView(ListView):
    """Vehicle search with availability"""
    
    model = Vehicle
    template_name = 'vehicles/vehicle_search.html'
    context_object_name = 'vehicles'
    paginate_by = 12
    
    def get_queryset(self):
        form = VehicleSearchForm(self.request.GET)
        queryset = Vehicle.objects.filter(is_active=True)
        
        if form.is_valid():
            pickup_date = form.cleaned_data.get('pickup_date')
            return_date = form.cleaned_data.get('return_date')
            pickup_location = form.cleaned_data.get('pickup_location')
            
            if pickup_date and return_date:
                queryset = queryset.available_for_period(pickup_date, return_date)
            
            if pickup_location:
                queryset = queryset.filter(location__icontains=pickup_location)
        
        # Apply additional filters
        self.filterset = VehicleFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = VehicleSearchForm(self.request.GET)
        context['filter'] = self.filterset
        return context


class VehicleCreateView(StaffRequiredMixin, CreateView):
    """Create new vehicle"""
    
    model = Vehicle
    form_class = VehicleForm
    template_name = 'vehicles/vehicle_form.html'
    success_url = reverse_lazy('vehicles:list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Vehicle created successfully!')
        return super().form_valid(form)


class VehicleUpdateView(StaffRequiredMixin, UpdateView):
    """Update vehicle"""
    
    model = Vehicle
    form_class = VehicleForm
    template_name = 'vehicles/vehicle_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Vehicle updated successfully!')
        return super().form_valid(form)


class VehicleDeleteView(StaffRequiredMixin, DeleteView):
    """Delete vehicle"""
    
    model = Vehicle
    template_name = 'vehicles/vehicle_confirm_delete.html'
    success_url = reverse_lazy('vehicles:list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Vehicle deleted successfully!')
        return super().delete(request, *args, **kwargs)


class VehicleReviewCreateView(CustomerRequiredMixin, CreateView):
    """Create vehicle review"""
    
    model = VehicleReview
    form_class = VehicleReviewForm
    template_name = 'vehicles/review_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.vehicle = get_object_or_404(Vehicle, pk=kwargs['vehicle_pk'])
        self.booking = get_object_or_404(
            Booking,
            pk=kwargs['booking_pk'],
            user=request.user,
            vehicle=self.vehicle,
            status='completed'
        )
        
        # Check if review already exists
        if VehicleReview.objects.filter(
            vehicle=self.vehicle,
            user=request.user,
            booking=self.booking
        ).exists():
            messages.error(request, 'You have already reviewed this vehicle.')
            return redirect('vehicles:detail', pk=self.vehicle.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.vehicle = self.vehicle
        form.instance.user = self.request.user
        form.instance.booking = self.booking
        messages.success(self.request, 'Thank you for your review!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return self.vehicle.get_absolute_url()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vehicle'] = self.vehicle
        context['booking'] = self.booking
        return context


# AJAX Views
@require_http_methods(["POST"])
@login_required
def check_vehicle_availability(request, pk):
    """Check vehicle availability via AJAX"""
    
    vehicle = get_object_or_404(Vehicle, pk=pk)
    form = VehicleAvailabilityForm(request.POST)
    
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        
        is_available = vehicle.is_available_for_period(
            start_date.date(), 
            end_date.date()
        )
        
        if is_available:
            # Calculate pricing
            duration = (end_date.date() - start_date.date()).days
            total_cost = vehicle.get_rate_for_duration(duration)
            
            return JsonResponse({
                'available': True,
                'duration_days': duration,
                'daily_rate': float(vehicle.daily_rate),
                'total_cost': float(total_cost),
                'security_deposit': float(vehicle.security_deposit),
                'message': f'Vehicle is available for {duration} day{"s" if duration != 1 else ""}'
            })
        else:
            return JsonResponse({
                'available': False,
                'message': 'Vehicle is not available for the selected dates'
            })
    else:
        return JsonResponse({
            'available': False,
            'message': 'Invalid date selection',
            'errors': form.errors
        }, status=400)


@require_http_methods(["GET"])
def get_vehicle_calendar(request, pk):
    """Get vehicle booking calendar data"""
    
    vehicle = get_object_or_404(Vehicle, pk=pk)
    
    # Get bookings for the next 3 months
    start_date = timezone.now().date()
    end_date = start_date + timezone.timedelta(days=90)
    
    bookings = Booking.objects.filter(
        vehicle=vehicle,
        status__in=['confirmed', 'active'],
        start_date__lte=end_date,
        end_date__gte=start_date
    ).values('start_date', 'end_date', 'status')
    
    # Format for calendar
    events = []
    for booking in bookings:
        events.append({
            'start': booking['start_date'].isoformat(),
            'end': booking['end_date'].isoformat(),
            'title': 'Booked',
            'color': '#dc3545' if booking['status'] == 'active' else '#ffc107'
        })
    
    return JsonResponse({'events': events})


@require_http_methods(["GET"])
def get_vehicles_by_category(request, category_id):
    """Get vehicles by category via AJAX"""
    
    category = get_object_or_404(VehicleCategory, pk=category_id)
    vehicles = Vehicle.objects.filter(
        category=category,
        is_active=True
    ).values('id', 'name', 'daily_rate', 'brand__name', 'model')
    
    return JsonResponse({
        'vehicles': list(vehicles),
        'category': category.name
    })


def vehicle_comparison(request):
    """Compare multiple vehicles"""
    
    vehicle_ids = request.GET.getlist('vehicles')
    if not vehicle_ids:
        messages.error(request, 'No vehicles selected for comparison.')
        return redirect('vehicles:list')
    
    vehicles = Vehicle.objects.filter(
        id__in=vehicle_ids,
        is_active=True
    ).select_related('brand', 'category').prefetch_related('features')
    
    if len(vehicles) < 2:
        messages.error(request, 'At least 2 vehicles are required for comparison.')
        return redirect('vehicles:list')
    
    # Get all unique features from selected vehicles
    all_features = VehicleFeature.objects.filter(
        vehicles__in=vehicles
    ).distinct().order_by('feature_type', 'name')
    
    context = {
        'vehicles': vehicles,
        'features': all_features,
    }
    
    return render(request, 'vehicles/vehicle_comparison.html', context)


# Staff/Admin Views
class VehicleMaintenanceListView(StaffRequiredMixin, ListView):
    """Vehicle maintenance records list"""
    
    model = VehicleMaintenanceRecord
    template_name = 'vehicles/maintenance_list.html'
    context_object_name = 'maintenance_records'
    paginate_by = 20
    
    def get_queryset(self):
        vehicle_id = self.kwargs.get('vehicle_pk')
        if vehicle_id:
            return VehicleMaintenanceRecord.objects.filter(
                vehicle_id=vehicle_id
            ).order_by('-service_date')
        return VehicleMaintenanceRecord.objects.all().order_by('-service_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle_id = self.kwargs.get('vehicle_pk')
        if vehicle_id:
            context['vehicle'] = get_object_or_404(Vehicle, pk=vehicle_id)
        return context


class VehicleMaintenanceCreateView(StaffRequiredMixin, CreateView):
    """Create maintenance record"""
    
    model = VehicleMaintenanceRecord
    form_class = VehicleMaintenanceForm
    template_name = 'vehicles/maintenance_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.vehicle = get_object_or_404(Vehicle, pk=kwargs['vehicle_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.vehicle = self.vehicle
        form.instance.performed_by = self.request.user
        
        # Update vehicle's next service information
        if form.instance.next_service_date:
            self.vehicle.next_service_date = form.instance.next_service_date
        if form.instance.next_service_mileage:
            self.vehicle.next_service_mileage = form.instance.next_service_mileage
        
        self.vehicle.last_service_date = form.instance.service_date
        self.vehicle.last_service_mileage = form.instance.mileage_at_service
        self.vehicle.save()
        
        messages.success(self.request, 'Maintenance record created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('vehicles:maintenance_list', kwargs={'vehicle_pk': self.vehicle.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vehicle'] = self.vehicle
        return context
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta

from rentals.utils import calculate_rental_days, calculate_total_amount
from .models import *
from .forms import *

def home(request):
    """Homepage with search form and featured content"""
    context = {
        'locations': Location.objects.filter(is_active=True),
        'vehicle_categories': VehicleCategory.objects.all(),
        'featured_vehicles': Vehicle.objects.filter(status='available')[:6],
        'featured_reviews': Review.objects.filter(is_featured=True)[:3],
    }
    return render(request, 'index.html', context)

def vehicles(request):
    """Vehicle listing with filters and search"""
    vehicles = Vehicle.objects.filter(status='available').select_related('category')
    
    # Filters
    category = request.GET.get('category')
    transmission = request.GET.get('transmission')
    fuel_type = request.GET.get('fuel_type')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    seats = request.GET.get('seats')
    search_query = request.GET.get('q')
    
    if category:
        vehicles = vehicles.filter(category_id=category)
    if transmission:
        vehicles = vehicles.filter(transmission=transmission)
    if fuel_type:
        vehicles = vehicles.filter(fuel_type=fuel_type)
    if min_price:
        vehicles = vehicles.filter(price_per_day__gte=min_price)
    if max_price:
        vehicles = vehicles.filter(price_per_day__lte=max_price)
    if seats:
        vehicles = vehicles.filter(seats__gte=seats)
    if search_query:
        vehicles = vehicles.filter(
            Q(make__icontains=search_query) |
            Q(model__icontains=search_query)
        )
    
    # Sorting
    sort_by = request.GET.get('sort', 'price_per_day')
    if sort_by == 'price_high':
        vehicles = vehicles.order_by('-price_per_day')
    elif sort_by == 'price_low':
        vehicles = vehicles.order_by('price_per_day')
    elif sort_by == 'newest':
        vehicles = vehicles.order_by('-year')
    else:
        vehicles = vehicles.order_by('price_per_day')
    
    # Pagination
    paginator = Paginator(vehicles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'vehicle_categories': VehicleCategory.objects.all(),
        'current_filters': {
            'category': category,
            'transmission': transmission,
            'fuel_type': fuel_type,
            'min_price': min_price,
            'max_price': max_price,
            'seats': seats,
            'search_query': search_query,
            'sort': sort_by,
        }
    }
    return render(request, 'vehicles.html', context)

def vehicle_detail(request, vehicle_id):
    """Individual vehicle detail page"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    related_vehicles = Vehicle.objects.filter(
        category=vehicle.category,
        status='available'
    ).exclude(id=vehicle_id)[:4]
    
    # Get average rating
    avg_rating = Review.objects.filter(
        booking__vehicle=vehicle
    ).aggregate(avg_rating=Avg('rating'))['avg_rating']
    
    context = {
        'vehicle': vehicle,
        'related_vehicles': related_vehicles,
        'avg_rating': avg_rating,
    }
    return render(request, 'vehicle_detail.html', context)

@login_required
def create_booking(request, vehicle_id):
    """Create a new booking"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.vehicle = vehicle
            booking.daily_rate = vehicle.price_per_day
            booking.security_deposit = vehicle.security_deposit
            
            # Calculate total amount
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            total_days = (end_date - start_date).days
            booking.total_days = total_days
            booking.total_amount = total_days * vehicle.price_per_day
            
            booking.save()
            
            messages.success(request, 'Booking created successfully!')
            return redirect('booking_confirmation', booking_id=booking.id)
    else:
        # Pre-fill dates from session if coming from search
        initial_data = {}
        if request.session.get('search_pickup_date'):
            initial_data['start_date'] = request.session['search_pickup_date']
        if request.session.get('search_dropoff_date'):
            initial_data['end_date'] = request.session['search_dropoff_date']
            
        form = BookingForm(initial=initial_data)
    
    context = {
        'form': form,
        'vehicle': vehicle,
        'locations': Location.objects.filter(is_active=True),
    }
    return render(request, 'booking.html', context)

@login_required
def dashboard(request):
    """User dashboard"""
    user_bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    
    # Statistics
    total_bookings = user_bookings.count()
    active_bookings = user_bookings.filter(status='active').count()
    total_spent = sum(booking.total_amount for booking in user_bookings if booking.status == 'completed')
    
    context = {
        'user_bookings': user_bookings[:5],  # Recent 5 bookings
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
        'total_spent': total_spent,
    }
    return render(request, 'dashboard.html', context)

def search_availability(request):
    """AJAX endpoint for real-time availability search"""
    if request.method == 'GET':
        pickup_date = request.GET.get('pickup_date')
        dropoff_date = request.GET.get('dropoff_date')
        vehicle_type = request.GET.get('vehicle_type')
        
        if pickup_date and dropoff_date:
            # Convert strings to datetime
            pickup = datetime.fromisoformat(pickup_date.replace('Z', '+00:00'))
            dropoff = datetime.fromisoformat(dropoff_date.replace('Z', '+00:00'))
            
            # Find available vehicles
            booked_vehicles = Booking.objects.filter(
                Q(start_date__lte=dropoff) & Q(end_date__gte=pickup),
                status__in=['confirmed', 'active']
            ).values_list('vehicle_id', flat=True)
            
            available_vehicles = Vehicle.objects.filter(
                status='available'
            ).exclude(id__in=booked_vehicles)
            
            if vehicle_type:
                available_vehicles = available_vehicles.filter(category_id=vehicle_type)
            
            # Calculate pricing for the period
            total_days = (dropoff - pickup).days
            vehicle_data = []
            
            for vehicle in available_vehicles:
                vehicle_data.append({
                    'id': str(vehicle.id),
                    'name': vehicle.display_name,
                    'category': vehicle.category.name,
                    'daily_rate': float(vehicle.price_per_day),
                    'total_price': float(vehicle.price_per_day * total_days),
                    'image': vehicle.images.first().image.url if vehicle.images.exists() else None,
                    'seats': vehicle.seats,
                    'transmission': vehicle.get_transmission_display(),
                    'fuel_type': vehicle.get_fuel_type_display(),
                })
            
            return JsonResponse({
                'success': True,
                'vehicles': vehicle_data,
                'total_days': total_days,
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# Add these functions to the existing views.py file

def vehicle_detail(request, vehicle_id):
    """Individual vehicle detail page with booking integration"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, status='available')
    related_vehicles = Vehicle.objects.filter(
        category=vehicle.category,
        status='available'
    ).exclude(id=vehicle_id)[:4]
    
    # Get average rating
    avg_rating = Review.objects.filter(
        booking__vehicle=vehicle
    ).aggregate(avg_rating=Avg('rating'))['avg_rating']
    
    # Get recent reviews
    recent_reviews = Review.objects.filter(
        booking__vehicle=vehicle
    ).order_by('-created_at')[:5]
    
    # Check if user has existing search parameters
    search_params = request.session.get('searchParams', {})
    
    context = {
        'vehicle': vehicle,
        'related_vehicles': related_vehicles,
        'avg_rating': avg_rating,
        'recent_reviews': recent_reviews,
        'search_params': search_params,
    }
    return render(request, 'vehicle_detail.html', context)

@login_required
def user_bookings(request):
    """User's booking history and management"""
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
    }
    return render(request, 'user_bookings.html', context)

@login_required
def booking_detail(request, booking_id):
    """Individual booking detail page"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    context = {
        'booking': booking,
    }
    return render(request, 'booking_detail.html', context)

@login_required
def booking_confirmation(request, booking_id):
    """Booking confirmation page"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    context = {
        'booking': booking,
    }
    return render(request, 'booking_confirmation.html', context)

@login_required
def user_profile(request):
    """User profile management"""
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    return render(request, 'profile.html', context)

def register(request):
    """User registration with profile creation"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            
            # Log the user in
            login(request, user)
            messages.success(request, 'Registration successful! Please complete your profile.')
            return redirect('contract_signing')
    else:
        form = CustomUserCreationForm()
    
    context = {'form': form}
    return render(request, 'auth/register.html', context)

@login_required
def contract_signing(request):
    """Contract signing page for new users"""
    try:
        profile = request.user.userprofile
        if profile.contract_signed:
            return redirect('dashboard')
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = ContractSigningForm(request.POST)
        if form.is_valid():
            profile.contract_signed = True
            profile.contract_signature = form.cleaned_data['signature']
            profile.save()
            
            messages.success(request, 'Contract signed successfully!')
            return redirect('dashboard')
    else:
        form = ContractSigningForm()
    
    context = {
        'form': form,
        'profile': profile,
    }
    return render(request, 'auth/contract_signing.html', context)

def locations(request):
    """Locations listing page"""
    locations_list = Location.objects.filter(is_active=True)
    
    context = {
        'locations': locations_list,
    }
    return render(request, 'locations.html', context)

def get_pricing(request):
    """AJAX endpoint for pricing calculation"""
    vehicle_id = request.GET.get('vehicle_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if vehicle_id and start_date and end_date:
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            total_days = calculate_rental_days(start, end)
            total_amount = calculate_total_amount(vehicle.price_per_day, total_days)
            
            return JsonResponse({
                'success': True,
                'daily_rate': float(vehicle.price_per_day),
                'total_days': total_days,
                'subtotal': float(total_amount),
                'security_deposit': float(vehicle.security_deposit),
                'total_amount': float(total_amount + vehicle.security_deposit),
            })
        except Vehicle.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Vehicle not found'})
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
    
    return JsonResponse({'success': False, 'error': 'Missing parameters'})

@login_required
def admin_panel(request):
    """Basic admin panel for staff users"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Dashboard statistics
    total_vehicles = Vehicle.objects.count()
    available_vehicles = Vehicle.objects.filter(status='available').count()
    total_bookings = Booking.objects.count()
    active_bookings = Booking.objects.filter(status='active').count()
    pending_bookings = Booking.objects.filter(status='pending').count()
    
    # Recent bookings
    recent_bookings = Booking.objects.select_related('user', 'vehicle').order_by('-created_at')[:10]
    
    context = {
        'total_vehicles': total_vehicles,
        'available_vehicles': available_vehicles,
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
        'pending_bookings': pending_bookings,
        'recent_bookings': recent_bookings,
    }
    return render(request, 'admin_panel.html', context)
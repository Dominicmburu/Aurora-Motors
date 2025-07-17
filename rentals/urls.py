from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Main pages
    path('', views.home, name='home'),
    path('vehicles/', views.vehicles, name='vehicles'),
    path('vehicle/<uuid:vehicle_id>/', views.vehicle_detail, name='vehicle_detail'),
    path('locations/', views.locations, name='locations'),
    
    # Booking
    path('book/<uuid:vehicle_id>/', views.create_booking, name='create_booking'),
    path('booking/<uuid:booking_id>/', views.booking_detail, name='booking_detail'),
    path('booking/<uuid:booking_id>/confirmation/', views.booking_confirmation, name='booking_confirmation'),
    
    # User dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('bookings/', views.user_bookings, name='bookings'),
    path('profile/', views.user_profile, name='profile'),
    
    # Authentication
    path('auth/login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('auth/register/', views.register, name='register'),
    path('auth/contract/', views.contract_signing, name='contract_signing'),
    
    # API endpoints
    path('api/', include('rentals.api_urls')),
    
    # Admin (for staff)
    path('admin-panel/', views.admin_panel, name='admin_panel'),
]
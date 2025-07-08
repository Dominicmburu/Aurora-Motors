from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile management
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('change-password/', views.change_password, name='change_password'),
    
    # History
    path('bookings/', views.BookingHistoryView.as_view(), name='booking_history'),
    path('activities/', views.ActivityHistoryView.as_view(), name='activity_history'),
    
    # API endpoints
    path('api/check-profile/', views.check_profile_completion, name='check_profile'),
    path('api/update-notifications/', views.update_notification_preferences, name='update_notifications'),
]
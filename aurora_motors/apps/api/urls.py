from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from . import views

# Create router for viewsets
router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'vehicles', views.VehicleViewSet)
router.register(r'bookings', views.BookingViewSet)
router.register(r'documents', views.DocumentViewSet)
router.register(r'contracts', views.ContractViewSet)
router.register(r'notifications', views.NotificationViewSet)

app_name = 'api'

urlpatterns = [
    # API root
    path('', views.APIRootView.as_view(), name='api_root'),
    
    # Authentication
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    path('auth/refresh/', views.RefreshTokenView.as_view(), name='token_refresh'),
    
    # API version 1
    path('v1/', include([
        # Include router URLs
        path('', include(router.urls)),
        
        # Custom endpoints
        path('dashboard/', views.DashboardAPIView.as_view(), name='dashboard'),
        path('vehicle-availability/', views.VehicleAvailabilityAPIView.as_view(), name='vehicle_availability'),
        path('booking-calendar/', views.BookingCalendarAPIView.as_view(), name='booking_calendar'),
        path('analytics/', views.AnalyticsAPIView.as_view(), name='analytics'),
        
        # User-specific endpoints
        path('profile/', views.UserProfileAPIView.as_view(), name='user_profile'),
        path('my-bookings/', views.UserBookingsAPIView.as_view(), name='user_bookings'),
        path('my-documents/', views.UserDocumentsAPIView.as_view(), name='user_documents'),
        path('my-notifications/', views.UserNotificationsAPIView.as_view(), name='user_notifications'),
    ])),
    
    # API documentation
    path('docs/', views.APIDocumentationView.as_view(), name='api_docs'),
]
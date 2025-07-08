from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    # Booking management
    path('', views.BookingListView.as_view(), name='list'),
    path('<int:pk>/', views.BookingDetailView.as_view(), name='detail'),
    path('vehicle/<int:vehicle_pk>/create/', views.BookingCreateView.as_view(), name='create'),
    path('<int:pk>/update/', views.BookingUpdateView.as_view(), name='update'),
    
    # Booking actions
    path('<int:pk>/cancel/', views.cancel_booking, name='cancel'),
    path('<int:pk>/extend/', views.extend_booking, name='extend'),
    path('<int:pk>/extension/<int:extension_pk>/process/', views.process_extension, name='process_extension'),
    
    # Vehicle operations
    path('<int:pk>/pickup/', views.vehicle_pickup, name='pickup'),
    path('<int:pk>/return/', views.vehicle_return, name='return'),
    
    # Additional features
    path('<int:pk>/add-note/', views.add_booking_note, name='add_note'),
    path('<int:pk>/add-driver/', views.add_additional_driver, name='add_driver'),
    path('<int:pk>/invoice/', views.booking_invoice_pdf, name='invoice'),
    
    # Staff dashboard and calendar
    path('dashboard/', views.BookingDashboardView.as_view(), name='dashboard'),
    path('calendar/', views.BookingCalendarView.as_view(), name='calendar'),
    
    # AJAX endpoints
    path('api/calendar-data/', views.booking_calendar_data, name='calendar_data'),
    path('api/statistics/', views.booking_statistics, name='statistics'),
    path('api/quick-check/', views.quick_booking_check, name='quick_check'),
]
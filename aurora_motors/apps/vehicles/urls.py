from django.urls import path
from . import views

app_name = 'vehicles'

urlpatterns = [
    # Public vehicle views
    path('', views.VehicleListView.as_view(), name='list'),
    path('<int:pk>/', views.VehicleDetailView.as_view(), name='detail'),
    path('search/', views.VehicleSearchView.as_view(), name='search'),
    path('compare/', views.vehicle_comparison, name='compare'),
    
    # Vehicle management (Staff only)
    path('create/', views.VehicleCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.VehicleUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.VehicleDeleteView.as_view(), name='delete'),
    
    # Reviews
    path('<int:vehicle_pk>/review/<int:booking_pk>/', 
         views.VehicleReviewCreateView.as_view(), name='create_review'),
    
    # Maintenance (Staff only)
    path('<int:vehicle_pk>/maintenance/', 
         views.VehicleMaintenanceListView.as_view(), name='maintenance_list'),
    path('<int:vehicle_pk>/maintenance/create/', 
         views.VehicleMaintenanceCreateView.as_view(), name='maintenance_create'),
    
    # AJAX endpoints
    path('<int:pk>/check-availability/', 
         views.check_vehicle_availability, name='check_availability'),
    path('<int:pk>/calendar/', 
         views.get_vehicle_calendar, name='calendar'),
    path('category/<int:category_id>/vehicles/', 
         views.get_vehicles_by_category, name='vehicles_by_category'),
]
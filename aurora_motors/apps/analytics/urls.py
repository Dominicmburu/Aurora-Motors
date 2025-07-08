from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Main dashboard
    path('', views.AnalyticsDashboardView.as_view(), name='dashboard'),
    
    # Reports
    path('reports/', views.ReportListView.as_view(), name='report_list'),
    path('reports/<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('reports/create/', views.ReportCreateView.as_view(), name='report_create'),
    path('reports/<int:pk>/edit/', views.ReportUpdateView.as_view(), name='report_edit'),
    path('reports/builder/', views.CustomReportBuilderView.as_view(), name='report_builder'),
    
    # KPIs
    path('kpis/', views.KPIDashboardView.as_view(), name='kpi_dashboard'),
    
    # User activity
    path('user-activity/', views.UserActivityView.as_view(), name='user_activity'),
    
    # AJAX endpoints
    path('api/booking-analytics/', views.booking_analytics_data, name='booking_analytics_data'),
    path('api/vehicle-utilization/', views.vehicle_utilization_data, name='vehicle_utilization_data'),
    path('api/revenue-analytics/', views.revenue_analytics_data, name='revenue_analytics_data'),
    path('api/reports/<int:pk>/generate/', views.generate_report, name='generate_report'),
    path('api/track-event/', views.track_event, name='track_event'),
]
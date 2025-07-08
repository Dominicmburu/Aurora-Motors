from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # User notification views
    path('', views.NotificationListView.as_view(), name='list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='detail'),
    path('preferences/', views.NotificationPreferenceView.as_view(), name='preferences'),
    
    # Staff/Admin views
    path('templates/', views.NotificationTemplateListView.as_view(), name='template_list'),
    path('templates/<int:pk>/', views.NotificationTemplateDetailView.as_view(), name='template_detail'),
    path('templates/create/', views.NotificationTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', views.NotificationTemplateUpdateView.as_view(), name='template_edit'),
    
    # Notification channels
    path('channels/', views.NotificationChannelListView.as_view(), name='channel_list'),
    path('channels/create/', views.NotificationChannelCreateView.as_view(), name='channel_create'),
    path('channels/<int:pk>/edit/', views.NotificationChannelUpdateView.as_view(), name='channel_edit'),
    
    # Management
    path('management/', views.NotificationManagementView.as_view(), name='management'),
    path('bulk-send/', views.bulk_notification_send, name='bulk_send'),
    path('test/', views.test_notification, name='test'),
    
    # Dashboard
    path('dashboard/', views.NotificationDashboardView.as_view(), name='dashboard'),
    
    # AJAX endpoints
    path('api/unread/', views.get_unread_notifications, name='unread'),
    path('api/<int:pk>/read/', views.mark_notification_read, name='mark_read'),
    path('api/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('api/statistics/', views.notification_statistics, name='statistics'),
    path('api/queue-status/', views.queue_status, name='queue_status'),
]
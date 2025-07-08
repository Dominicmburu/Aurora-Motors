from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from apps.core.views import HomeView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Core pages
    path('', HomeView.as_view(), name='home'),
    path('about/', TemplateView.as_view(template_name='pages/about.html'), name='about'),
    path('contact/', TemplateView.as_view(template_name='pages/contact.html'), name='contact'),
    path('privacy/', TemplateView.as_view(template_name='pages/privacy.html'), name='privacy'),
    path('terms/', TemplateView.as_view(template_name='pages/terms.html'), name='terms'),
    
    # Apps
    path('accounts/', include('apps.accounts.urls')),
    path('vehicles/', include('apps.vehicles.urls')),
    path('bookings/', include('apps.bookings.urls')),
    path('contracts/', include('apps.contracts.urls')),
    path('documents/', include('apps.documents.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('analytics/', include('apps.analytics.urls')),
    
    # API
    path('api/', include('apps.api.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Add debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# Custom error pages
handler404 = 'apps.core.views.custom_404'
handler500 = 'apps.core.views.custom_500'
handler403 = 'apps.core.views.custom_403'

# Admin customization
admin.site.site_header = 'Aurora Motors Administration'
admin.site.site_title = 'Aurora Motors Admin'
admin.site.index_title = 'Welcome to Aurora Motors Administration'

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
# from rentals.sitemaps import CarSitemap, StaticViewSitemap

# sitemaps = {
#     'cars': CarSitemap,
#     'static': StaticViewSitemap,
# }

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('rentals.urls')),
    path('api/', include('rentals.api_urls')),
    # path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# # Custom error handlers
# handler404 = 'rentals.views.custom_404'
# handler500 = 'rentals.views.custom_500'
# handler403 = 'rentals.views.custom_403'
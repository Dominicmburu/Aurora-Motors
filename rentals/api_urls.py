from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'vehicles', api_views.VehicleViewSet, basename='vehicle')
router.register(r'bookings', api_views.BookingViewSet, basename='booking')
router.register(r'categories', api_views.VehicleCategoryViewSet, basename='category')
router.register(r'locations', api_views.LocationViewSet, basename='location')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', api_views.search_availability, name='search_availability'),
    path('pricing/', api_views.get_pricing, name='get_pricing'),
    path('booking/<uuid:booking_id>/cancel/', api_views.cancel_booking, name='cancel_booking'),
    path('contract/sign/', api_views.sign_contract, name='sign_contract'),
]
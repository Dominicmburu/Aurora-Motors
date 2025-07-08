from rest_framework import serializers
from apps.accounts.models import CustomUser
from apps.vehicles.models import Vehicle
from apps.bookings.models import Booking

class APIUserSerializer(serializers.ModelSerializer):
    """User serializer for API"""
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'user_type', 'is_verified', 'date_joined'
        ]
        read_only_fields = ['id', 'username', 'user_type', 'is_verified', 'date_joined']

class APIVehicleSerializer(serializers.ModelSerializer):
    """Vehicle serializer for API"""
    
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'name', 'brand_name', 'category_name', 'model', 'year',
            'transmission', 'fuel_type', 'seats', 'doors', 'daily_rate',
            'weekly_rate', 'monthly_rate', 'is_featured'
        ]

class APIBookingSerializer(serializers.ModelSerializer):
    """Booking serializer for API"""
    
    vehicle_name = serializers.CharField(source='vehicle.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'vehicle_name', 'user_name',
            'start_date', 'end_date', 'pickup_location', 'return_location',
            'status', 'total_amount', 'created_at'
        ]
        read_only_fields = ['id', 'booking_number', 'user_name', 'created_at']
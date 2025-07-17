from rest_framework import serializers
from .models import Vehicle, Booking, VehicleCategory, Location, VehicleImage

class VehicleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleImage
        fields = ['image', 'alt_text', 'is_primary']

class VehicleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleCategory
        fields = ['id', 'name', 'description', 'icon']

class VehicleSerializer(serializers.ModelSerializer):
    images = VehicleImageSerializer(many=True, read_only=True)
    category = VehicleCategorySerializer(read_only=True)
    display_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'display_name', 'make', 'model', 'year', 'category',
            'transmission', 'fuel_type', 'seats', 'doors', 'price_per_day',
            'security_deposit', 'mileage', 'features', 'images'
        ]

class BookingSerializer(serializers.ModelSerializer):
    vehicle = VehicleSerializer(read_only=True)
    booking_number = serializers.CharField(read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'vehicle', 'start_date', 'end_date',
            'pickup_location', 'dropoff_location', 'total_days', 'daily_rate',
            'total_amount', 'security_deposit', 'status', 'special_requests',
            'created_at'
        ]

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            'id', 'name', 'address', 'city', 'state', 'postal_code',
            'phone', 'operating_hours', 'latitude', 'longitude'
        ]
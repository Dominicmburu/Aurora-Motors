from rest_framework import serializers
from .models import Booking, BookingExtension, BookingAdditionalDriver

class BookingSerializer(serializers.ModelSerializer):
    vehicle_name = serializers.CharField(source='vehicle.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    can_be_cancelled = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'vehicle', 'vehicle_name', 'user_name',
            'start_date', 'end_date', 'pickup_location', 'return_location',
            'status', 'total_days', 'total_amount', 'special_requests',
            'can_be_cancelled', 'is_overdue', 'created_at'
        ]
        read_only_fields = ['booking_number', 'total_days', 'total_amount', 'created_at']

class BookingExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingExtension
        fields = [
            'id', 'original_end_date', 'new_end_date', 'additional_days',
            'additional_amount', 'reason', 'status', 'created_at'
        ]

class BookingAdditionalDriverSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.get_full_name', read_only=True)
    
    class Meta:
        model = BookingAdditionalDriver
        fields = [
            'id', 'driver', 'driver_name', 'license_number', 
            'license_expiry', 'is_approved'
        ]
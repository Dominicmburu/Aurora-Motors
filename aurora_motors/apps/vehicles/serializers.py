from rest_framework import serializers
from .models import (
    Vehicle, VehicleCategory, VehicleBrand, VehicleImage, 
    VehicleFeature, VehicleReview, VehicleMaintenanceRecord
)

class VehicleCategorySerializer(serializers.ModelSerializer):
    vehicle_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = VehicleCategory
        fields = ['id', 'name', 'description', 'icon', 'vehicle_count']

class VehicleBrandSerializer(serializers.ModelSerializer):
    vehicle_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = VehicleBrand
        fields = ['id', 'name', 'logo', 'country', 'vehicle_count']

class VehicleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleImage
        fields = ['id', 'image', 'caption', 'is_primary', 'sort_order']

class VehicleFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleFeature
        fields = ['id', 'name', 'description', 'feature_type', 'icon']

class VehicleListSerializer(serializers.ModelSerializer):
    brand = VehicleBrandSerializer(read_only=True)
    category = VehicleCategorySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'name', 'brand', 'category', 'model', 'year',
            'transmission', 'fuel_type', 'seats', 'doors',
            'daily_rate', 'weekly_rate', 'monthly_rate',
            'is_featured', 'primary_image', 'average_rating', 'review_count'
        ]
    
    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return VehicleImageSerializer(primary_image).data
        return None
    
    def get_average_rating(self, obj):
        return obj.reviews.filter(is_approved=True).aggregate(
            avg_rating=models.Avg('rating')
        )['avg_rating'] or 0
    
    def get_review_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()

class VehicleDetailSerializer(VehicleListSerializer):
    images = VehicleImageSerializer(many=True, read_only=True)
    features = VehicleFeatureSerializer(many=True, read_only=True)
    recent_reviews = serializers.SerializerMethodField()
    
    class Meta(VehicleListSerializer.Meta):
        fields = VehicleListSerializer.Meta.fields + [
            'registration_number', 'color', 'mileage', 'condition',
            'security_deposit', 'description', 'location',
            'images', 'features', 'recent_reviews'
        ]
    
    def get_recent_reviews(self, obj):
        recent_reviews = obj.reviews.filter(is_approved=True)[:5]
        return VehicleReviewSerializer(recent_reviews, many=True).data

class VehicleReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = VehicleReview
        fields = [
            'id', 'rating', 'title', 'content', 'cleanliness_rating',
            'comfort_rating', 'performance_rating', 'user_name', 'created_at'
        ]

class VehicleMaintenanceSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    
    class Meta:
        model = VehicleMaintenanceRecord
        fields = [
            'id', 'maintenance_type', 'description', 'cost',
            'service_date', 'service_provider', 'performed_by_name'
        ]
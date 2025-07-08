from rest_framework import serializers
from .models import CustomUser, UserProfile, UserActivity

class UserSerializer(serializers.ModelSerializer):
    """User serializer"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'date_of_birth', 'age', 'address', 'user_type',
            'is_verified', 'profile_completed', 'avatar', 'date_joined'
        ]
        read_only_fields = ['id', 'username', 'user_type', 'is_verified', 'date_joined']

class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer"""
    
    user = UserSerializer(read_only=True)
    is_license_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = '__all__'

class UserActivitySerializer(serializers.ModelSerializer):
    """User activity serializer"""
    
    user = serializers.StringRelatedField()
    
    class Meta:
        model = UserActivity
        fields = '__all__'
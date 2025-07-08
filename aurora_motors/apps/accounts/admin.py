from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import CustomUser, UserProfile, UserActivity

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Custom user admin"""
    
    list_display = [
        'email', 'get_full_name', 'user_type', 'is_verified', 
        'profile_completed', 'date_joined', 'last_login'
    ]
    list_filter = [
        'user_type', 'is_verified', 'profile_completed', 
        'is_staff', 'is_active', 'date_joined'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'username']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 
                      'date_of_birth', 'address', 'avatar')
        }),
        ('Permissions', {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser',
                      'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Status', {
            'fields': ('is_verified', 'profile_completed', 'receive_notifications',
                      'receive_marketing')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'
    
    actions = ['verify_users', 'unverify_users']
    
    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} users verified.')
    verify_users.short_description = 'Verify selected users'
    
    def unverify_users(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} users unverified.')
    unverify_users.short_description = 'Unverify selected users'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """User profile admin"""
    
    list_display = [
        'user', 'license_number', 'license_expiry', 'is_license_valid',
        'total_bookings', 'total_spent', 'company_name'
    ]
    list_filter = [
        'license_country', 'preferred_vehicle_type', 'preferred_transmission'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'license_number', 'company_name'
    ]
    readonly_fields = ['total_bookings', 'total_spent', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone',
                      'emergency_contact_relationship')
        }),
        ('Driver Information', {
            'fields': ('license_number', 'license_expiry', 'license_country')
        }),
        ('Company Information', {
            'fields': ('company_name', 'company_abn', 'company_address')
        }),
        ('Statistics', {
            'fields': ('total_bookings', 'total_spent')
        }),
        ('Preferences', {
            'fields': ('preferred_vehicle_type', 'preferred_transmission')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def is_license_valid(self, obj):
        if obj.is_license_valid:
            return format_html('<span style="color: green;">Valid</span>')
        return format_html('<span style="color: red;">Invalid/Expired</span>')
    is_license_valid.short_description = 'License Status'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """User activity admin"""
    
    list_display = [
        'user', 'activity_type', 'created_at', 'ip_address'
    ]
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
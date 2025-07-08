from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from .models import (
    VehicleCategory, VehicleBrand, Vehicle, VehicleImage, 
    VehicleFeature, VehicleFeatureAssignment, VehicleReview,
    VehicleMaintenanceRecord
)

@admin.register(VehicleCategory)
class VehicleCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'vehicle_count', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['sort_order', 'name']
    
    def vehicle_count(self, obj):
        return obj.vehicles.count()
    vehicle_count.short_description = 'Vehicles'


@admin.register(VehicleBrand)
class VehicleBrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'vehicle_count', 'is_active']
    list_filter = ['country', 'is_active']
    search_fields = ['name', 'country']
    ordering = ['name']
    
    def vehicle_count(self, obj):
        return obj.vehicles.count()
    vehicle_count.short_description = 'Vehicles'


class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1
    fields = ['image', 'caption', 'is_primary', 'sort_order']


class VehicleFeatureInline(admin.TabularInline):
    model = VehicleFeatureAssignment
    extra = 1
    fields = ['feature', 'value']


class VehicleMaintenanceInline(admin.TabularInline):
    model = VehicleMaintenanceRecord
    extra = 0
    fields = ['maintenance_type', 'service_date', 'cost', 'description']
    readonly_fields = ['service_date']
    ordering = ['-service_date']


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        'registration_number', 'full_name', 'category', 'status', 
        'daily_rate', 'is_featured', 'is_active', 'booking_count'
    ]
    list_filter = [
        'status', 'is_active', 'is_featured', 'category', 'brand', 
        'transmission', 'fuel_type', 'year'
    ]
    search_fields = [
        'name', 'registration_number', 'vin', 'brand__name', 'model'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'brand', 'category', 'model', 'year')
        }),
        ('Technical Specifications', {
            'fields': ('transmission', 'fuel_type', 'engine_size', 'seats', 'doors')
        }),
        ('Vehicle Details', {
            'fields': ('registration_number', 'vin', 'color', 'mileage', 'condition')
        }),
        ('Pricing', {
            'fields': ('daily_rate', 'weekly_rate', 'monthly_rate', 'security_deposit')
        }),
        ('Status', {
            'fields': ('status', 'is_featured', 'is_active')
        }),
        ('Location', {
            'fields': ('location', 'latitude', 'longitude')
        }),
        ('Maintenance', {
            'fields': ('last_service_date', 'next_service_date', 
                      'last_service_mileage', 'next_service_mileage')
        }),
        ('Insurance', {
            'fields': ('insurance_company', 'insurance_policy', 'insurance_expiry')
        }),
        ('Additional Information', {
            'fields': ('description', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [VehicleImageInline, VehicleFeatureInline, VehicleMaintenanceInline]
    
    actions = ['mark_as_available', 'mark_as_maintenance', 'mark_as_featured']
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Vehicle'
    
    def booking_count(self, obj):
        return obj.bookings.count()
    booking_count.short_description = 'Bookings'
    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(status='available')
        self.message_user(request, f'{updated} vehicles marked as available.')
    mark_as_available.short_description = 'Mark selected vehicles as available'
    
    def mark_as_maintenance(self, request, queryset):
        updated = queryset.update(status='maintenance')
        self.message_user(request, f'{updated} vehicles marked for maintenance.')
    mark_as_maintenance.short_description = 'Mark selected vehicles for maintenance'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} vehicles marked as featured.')
    mark_as_featured.short_description = 'Mark selected vehicles as featured'


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'caption', 'is_primary', 'sort_order', 'image_preview']
    list_filter = ['is_primary', 'vehicle__brand']
    search_fields = ['vehicle__name', 'caption']
    ordering = ['vehicle', 'sort_order']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.image.url
            )
        return 'No image'
    image_preview.short_description = 'Preview'


@admin.register(VehicleFeature)
class VehicleFeatureAdmin(admin.ModelAdmin):
    list_display = ['name', 'feature_type', 'is_active', 'vehicle_count']
    list_filter = ['feature_type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['feature_type', 'name']
    
    def vehicle_count(self, obj):
        return obj.vehicles.count()
    vehicle_count.short_description = 'Vehicles'


@admin.register(VehicleReview)
class VehicleReviewAdmin(admin.ModelAdmin):
    list_display = [
        'vehicle', 'user', 'rating', 'title', 'is_approved', 
        'is_featured', 'created_at'
    ]
    list_filter = ['rating', 'is_approved', 'is_featured', 'created_at']
    search_fields = ['vehicle__name', 'user__email', 'title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Review Information', {
            'fields': ('vehicle', 'user', 'booking')
        }),
        ('Rating', {
            'fields': ('rating', 'cleanliness_rating', 'comfort_rating', 'performance_rating')
        }),
        ('Content', {
            'fields': ('title', 'content')
        }),
        ('Status', {
            'fields': ('is_approved', 'is_featured')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_reviews', 'unapprove_reviews', 'mark_as_featured']
    
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} reviews approved.')
    approve_reviews.short_description = 'Approve selected reviews'
    
    def unapprove_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} reviews unapproved.')
    unapprove_reviews.short_description = 'Unapprove selected reviews'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} reviews marked as featured.')
    mark_as_featured.short_description = 'Mark selected reviews as featured'


@admin.register(VehicleMaintenanceRecord)
class VehicleMaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = [
        'vehicle', 'maintenance_type', 'service_date', 'cost', 
        'service_provider', 'performed_by'
    ]
    list_filter = ['maintenance_type', 'service_date', 'service_provider']
    search_fields = ['vehicle__name', 'description', 'service_provider']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'service_date'
    
    fieldsets = (
        ('Vehicle & Service', {
            'fields': ('vehicle', 'maintenance_type', 'service_date')
        }),
        ('Service Details', {
            'fields': ('description', 'cost', 'mileage_at_service')
        }),
        ('Next Service', {
            'fields': ('next_service_date', 'next_service_mileage')
        }),
        ('Service Provider', {
            'fields': ('service_provider', 'service_provider_contact', 'invoice_number')
        }),
        ('Internal', {
            'fields': ('performed_by', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
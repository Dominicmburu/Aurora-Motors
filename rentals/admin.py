from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import *

@admin.register(VehicleCategory)
class VehicleCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'icon']
    search_fields = ['name']

class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1
    fields = ['image', 'is_primary', 'alt_text']

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'category', 'status', 'price_per_day', 
        'transmission', 'fuel_type', 'seats', 'created_at'
    ]
    list_filter = [
        'status', 'category', 'transmission', 'fuel_type', 
        'seats', 'created_at'
    ]
    search_fields = ['make', 'model', 'license_plate', 'vin_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [VehicleImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('make', 'model', 'year', 'category', 'status')
        }),
        ('Specifications', {
            'fields': ('transmission', 'fuel_type', 'seats', 'doors', 'mileage', 'features')
        }),
        ('Pricing', {
            'fields': ('price_per_day', 'security_deposit')
        }),
        ('Legal Information', {
            'fields': ('license_plate', 'vin_number', 'insurance_expiry', 'registration_expiry')
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'phone', 'city', 'license_number', 
        'contract_signed', 'created_at'
    ]
    list_filter = ['contract_signed', 'city', 'state', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone', 'license_number']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Contact Information', {
            'fields': ('phone', 'address', 'city', 'state', 'postal_code')
        }),
        ('License Information', {
            'fields': ('license_number', 'license_expiry', 'license_image', 'id_document')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone')
        }),
        ('Contract Information', {
            'fields': ('contract_signed', 'contract_signature')
        }),
        ('System Information', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_number', 'user', 'vehicle', 'start_date', 
        'end_date', 'status', 'total_amount', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'start_date']
    search_fields = [
        'user__username', 'user__email', 'vehicle__make', 
        'vehicle__model', 'pickup_location', 'dropoff_location'
    ]
    readonly_fields = ['id', 'booking_number', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('id', 'booking_number', 'user', 'vehicle', 'status')
        }),
        ('Rental Period', {
            'fields': ('start_date', 'end_date', 'total_days')
        }),
        ('Locations', {
            'fields': ('pickup_location', 'dropoff_location')
        }),
        ('Pricing', {
            'fields': ('daily_rate', 'total_amount', 'security_deposit')
        }),
        ('Additional Information', {
            'fields': ('special_requests',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'vehicle')
    
    actions = ['confirm_bookings', 'cancel_bookings']
    
    def confirm_bookings(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} bookings confirmed.')
    confirm_bookings.short_description = "Confirm selected bookings"
    
    def cancel_bookings(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} bookings cancelled.')
    cancel_bookings.short_description = "Cancel selected bookings"

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'booking', 'amount', 'payment_method', 'status', 
        'transaction_id', 'payment_date'
    ]
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['booking__id', 'transaction_id']
    readonly_fields = ['payment_date']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'booking', 'rating', 'title', 'is_featured', 'created_at'
    ]
    list_filter = ['rating', 'is_featured', 'created_at']
    search_fields = ['title', 'comment', 'booking__user__username']
    actions = ['make_featured', 'remove_featured']
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} reviews marked as featured.')
    make_featured.short_description = "Mark as featured"
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} reviews removed from featured.')
    remove_featured.short_description = "Remove from featured"

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'phone', 'is_active']
    list_filter = ['is_active', 'city', 'state']
    search_fields = ['name', 'address', 'city']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'postal_code')
        }),
        ('Contact Information', {
            'fields': ('phone', 'operating_hours')
        }),
        ('Location Coordinates', {
            'fields': ('latitude', 'longitude'),
            'description': 'GPS coordinates for map display'
        }),
    )

# Customize admin site
admin.site.site_header = "Aurora Motors Administration"
admin.site.site_title = "Aurora Motors Admin"
admin.site.index_title = "Welcome to Aurora Motors Administration"
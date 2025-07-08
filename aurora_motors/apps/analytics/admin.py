from django.contrib import admin
from django.utils.html import format_html
from .models import AnalyticsEvent, Report, Dashboard, KPI, Metric

@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = [
        'category', 'action', 'label', 'user', 'created_at', 'ip_address'
    ]
    list_filter = ['category', 'action', 'created_at']
    search_fields = ['label', 'user__email', 'path']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'report_type', 'created_by', 'is_scheduled', 
        'is_public', 'last_generated', 'created_at'
    ]
    list_filter = ['report_type', 'is_scheduled', 'is_public', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['last_generated', 'created_at', 'updated_at']

@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'current_value', 'target_value', 'format_display',
        'update_frequency', 'last_updated', 'is_active'
    ]
    list_filter = ['format_type', 'update_frequency', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['current_value', 'previous_value', 'last_updated']
    
    def format_display(self, obj):
        if obj.format_type == 'percentage' and obj.current_value:
            return f"{obj.current_value:.1f}%"
        elif obj.format_type == 'currency' and obj.current_value:
            return f"${obj.current_value:,.2f}"
        return obj.current_value
    format_display.short_description = 'Current Value'
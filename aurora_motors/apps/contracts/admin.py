from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    ContractTemplate, Contract, ContractSignature, ContractRevision,
    ContractAuditLog, ContractReminder, ContractAnalytics
)

@admin.register(ContractTemplate)
class ContractTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'template_type', 'version', 'is_active', 'is_required',
        'contract_count', 'created_at'
    ]
    list_filter = ['template_type', 'is_active', 'is_required', 'created_at']
    search_fields = ['name', 'template_type']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'template_type', 'version', 'created_by')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Settings', {
            'fields': ('is_active', 'is_required', 'requires_signature', 
                      'requires_witness', 'requires_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def contract_count(self, obj):
        return obj.contracts.count()
    contract_count.short_description = 'Contracts Created'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            contract_count=Count('contracts')
        )


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user', 'template', 'status', 'sent_date', 'signed_date',
        'expires_at', 'created_at'
    ]
    list_filter = ['status', 'template__template_type', 'created_at', 'signed_date']
    search_fields = [
        'title', 'user__email', 'user__first_name', 'user__last_name',
        'booking__booking_number'
    ]
    readonly_fields = [
        'contract_id', 'sent_date', 'signed_date', 'signature_data',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Contract Information', {
            'fields': ('contract_id', 'template', 'booking', 'user', 'status')
        }),
        ('Content', {
            'fields': ('title', 'content')
        }),
        ('Signing Information', {
            'fields': ('sent_date', 'signed_date', 'expires_at', 'signature_data',
                      'signature_ip', 'signature_user_agent')
        }),
        ('Files', {
            'fields': ('pdf_file', 'signed_pdf_file')
        }),
        ('Metadata', {
            'fields': ('notes', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['send_for_signature', 'cancel_contracts']
    
    def send_for_signature(self, request, queryset):
        updated = 0
        for contract in queryset.filter(status='draft'):
            contract.send_for_signature()
            updated += 1
        self.message_user(request, f'{updated} contracts sent for signature.')
    send_for_signature.short_description = 'Send selected contracts for signature'
    
    def cancel_contracts(self, request, queryset):
        updated = queryset.filter(
            status__in=['draft', 'sent']
        ).update(status='cancelled')
        self.message_user(request, f'{updated} contracts cancelled.')
    cancel_contracts.short_description = 'Cancel selected contracts'


@admin.register(ContractSignature)
class ContractSignatureAdmin(admin.ModelAdmin):
    list_display = [
        'contract', 'signer', 'signature_type', 'signature_date', 'ip_address'
    ]
    list_filter = ['signature_type', 'signature_date']
    search_fields = ['contract__title', 'signer__email']
    readonly_fields = ['signature_date', 'ip_address', 'user_agent']


@admin.register(ContractRevision)
class ContractRevisionAdmin(admin.ModelAdmin):
    list_display = [
        'contract', 'revision_number', 'changed_by', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['contract__title', 'changed_by__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ContractAuditLog)
class ContractAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'contract', 'user', 'action', 'created_at', 'ip_address'
    ]
    list_filter = ['action', 'created_at']
    search_fields = ['contract__title', 'user__email', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ContractReminder)
class ContractReminderAdmin(admin.ModelAdmin):
    list_display = [
        'contract', 'reminder_date', 'is_sent', 'sent_date', 'subject'
    ]
    list_filter = ['is_sent', 'reminder_date']
    search_fields = ['contract__title', 'subject']
    readonly_fields = ['sent_date']
    
    actions = ['send_reminders']
    
    def send_reminders(self, request, queryset):
        updated = 0
        for reminder in queryset.filter(is_sent=False):
            reminder.send_reminder()
            updated += 1
        self.message_user(request, f'{updated} reminders sent.')
    send_reminders.short_description = 'Send selected reminders'


@admin.register(ContractAnalytics)
class ContractAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'contract', 'view_count', 'sign_attempts', 'time_to_sign',
        'download_count'
    ]
    search_fields = ['contract__title']
    readonly_fields = [
        'view_count', 'unique_viewers', 'first_viewed', 'last_viewed',
        'time_to_sign', 'sign_attempts', 'download_count'
    ]
    
    def has_add_permission(self, request):
        return False
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    DocumentCategory, Document, DocumentVersion, DocumentShare,
    DocumentAuditLog, DocumentTemplate
)

@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'is_required', 'is_active', 'document_count',
        'max_file_size_display', 'sort_order'
    ]
    list_filter = ['is_required', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    
    def document_count(self, obj):
        return obj.documents.count()
    document_count.short_description = 'Documents'
    
    def max_file_size_display(self, obj):
        if obj.max_file_size:
            return f"{obj.max_file_size / (1024 * 1024):.1f} MB"
        return "No limit"
    max_file_size_display.short_description = 'Max File Size'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            document_count=Count('documents')
        )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user', 'document_type', 'category', 'status',
        'file_size_display', 'expiry_date', 'is_verified', 'created_at'
    ]
    list_filter = [
        'status', 'document_type', 'category', 'is_verified',
        'created_at', 'expiry_date'
    ]
    search_fields = [
        'name', 'user__email', 'user__first_name', 'user__last_name',
        'document_number', 'issuing_authority'
    ]
    readonly_fields = [
        'file_size', 'original_filename', 'mime_type', 'checksum',
        'verification_date', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Document Information', {
            'fields': ('user', 'category', 'document_type', 'name', 'description')
        }),
        ('File Information', {
            'fields': ('file', 'file_size', 'original_filename', 'mime_type', 'checksum')
        }),
        ('Document Details', {
            'fields': ('issue_date', 'expiry_date', 'issuing_authority', 'document_number')
        }),
        ('Status', {
            'fields': ('status', 'is_verified', 'verification_date', 'verified_by')
        }),
        ('Review Information', {
            'fields': ('review_notes', 'rejection_reason')
        }),
        ('Access Control', {
            'fields': ('is_public', 'is_sensitive')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_documents', 'reject_documents', 'mark_expired']
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "Unknown"
    file_size_display.short_description = 'File Size'
    
    def approve_documents(self, request, queryset):
        updated = 0
        for document in queryset.filter(status='pending'):
            document.approve(request.user, 'Bulk approval by admin')
            updated += 1
        self.message_user(request, f'{updated} documents approved.')
    approve_documents.short_description = 'Approve selected documents'
    
    def reject_documents(self, request, queryset):
        updated = 0
        for document in queryset.filter(status='pending'):
            document.reject(request.user, 'Bulk rejection by admin', 'Rejected by admin')
            updated += 1
        self.message_user(request, f'{updated} documents rejected.')
    reject_documents.short_description = 'Reject selected documents'
    
    def mark_expired(self, request, queryset):
        updated = 0
        for document in queryset:
            if document.is_expired:
                document.mark_expired()
                updated += 1
        self.message_user(request, f'{updated} documents marked as expired.')
    mark_expired.short_description = 'Mark expired documents'


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = [
        'document', 'version_number', 'uploaded_by', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['document__name', 'uploaded_by__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    list_display = [
        'document', 'shared_with', 'shared_by', 'access_type',
        'is_active', 'expires_at', 'access_count'
    ]
    list_filter = ['access_type', 'is_active', 'expires_at']
    search_fields = [
        'document__name', 'shared_with__email', 'shared_by__email'
    ]
    readonly_fields = ['access_count', 'last_accessed', 'created_at', 'updated_at']


@admin.register(DocumentAuditLog)
class DocumentAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'document', 'user', 'action', 'created_at', 'ip_address'
    ]
    list_filter = ['action', 'created_at']
    search_fields = ['document__name', 'user__email', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'template_type', 'is_active', 'created_at'
    ]
    list_filter = ['template_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
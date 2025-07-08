from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from apps.core.models import TimeStampedModel
import os

def user_document_path(instance, filename):
    """Generate upload path for user documents"""
    return f"documents/{instance.user.id}/{instance.document_type}/{filename}"

class DocumentCategory(TimeStampedModel):
    """Document category model"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    # File restrictions
    allowed_extensions = models.JSONField(
        default=list,
        help_text="List of allowed file extensions (e.g., ['pdf', 'jpg', 'png'])"
    )
    max_file_size = models.PositiveIntegerField(
        default=10485760,  # 10MB
        help_text="Maximum file size in bytes"
    )
    
    class Meta:
        verbose_name = 'Document Category'
        verbose_name_plural = 'Document Categories'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class Document(TimeStampedModel):
    """Document model"""
    
    DOCUMENT_TYPES = (
        ('license', 'Driver License'),
        ('passport', 'Passport'),
        ('id_card', 'ID Card'),
        ('insurance', 'Insurance Document'),
        ('bank_statement', 'Bank Statement'),
        ('utility_bill', 'Utility Bill'),
        ('employment_letter', 'Employment Letter'),
        ('rental_agreement', 'Rental Agreement'),
        ('damage_report', 'Damage Report'),
        ('inspection_report', 'Inspection Report'),
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )
    
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True
    )
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    
    # Document details
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=user_document_path)
    file_size = models.PositiveIntegerField(default=0)
    
    # Status and verification
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
    )
    
    # Document validity
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    issuing_authority = models.CharField(max_length=200, blank=True)
    document_number = models.CharField(max_length=100, blank=True)
    
    # Review information
    review_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Metadata
    original_filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    checksum = models.CharField(max_length=64, blank=True)  # SHA-256 hash
    
    # Access control
    is_public = models.BooleanField(default=False)
    is_sensitive = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'document_type']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.get_full_name()}"
    
    def get_absolute_url(self):
        return reverse('documents:detail', kwargs={'pk': self.pk})
    
    def clean(self):
        """Validate document"""
        if self.file:
            # Check file size
            if self.category and self.category.max_file_size:
                if self.file.size > self.category.max_file_size:
                    raise ValidationError(
                        f'File size exceeds maximum allowed size of '
                        f'{self.category.max_file_size / 1024 / 1024:.1f}MB'
                    )
            
            # Check file extension
            if self.category and self.category.allowed_extensions:
                file_extension = os.path.splitext(self.file.name)[1][1:].lower()
                if file_extension not in self.category.allowed_extensions:
                    raise ValidationError(
                        f'File type .{file_extension} is not allowed. '
                        f'Allowed types: {", ".join(self.category.allowed_extensions)}'
                    )
        
        # Validate dates
        if self.issue_date and self.expiry_date:
            if self.issue_date >= self.expiry_date:
                raise ValidationError('Expiry date must be after issue date.')
    
    def save(self, *args, **kwargs):
        if self.file:
            # Store original filename and file size
            self.original_filename = self.file.name
            self.file_size = self.file.size
            
            # Generate checksum
            if not self.checksum:
                import hashlib
                self.file.seek(0)
                self.checksum = hashlib.sha256(self.file.read()).hexdigest()
                self.file.seek(0)
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False
    
    @property
    def days_until_expiry(self):
        """Get days until expiry"""
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None
    
    @property
    def file_extension(self):
        """Get file extension"""
        if self.file:
            return os.path.splitext(self.file.name)[1][1:].lower()
        return ''
    
    @property
    def formatted_file_size(self):
        """Get formatted file size"""
        if self.file_size:
            if self.file_size < 1024:
                return f"{self.file_size} B"
            elif self.file_size < 1024 * 1024:
                return f"{self.file_size / 1024:.1f} KB"
            else:
                return f"{self.file_size / (1024 * 1024):.1f} MB"
        return "Unknown"
    
    def approve(self, verified_by, notes=''):
        """Approve the document"""
        self.status = 'approved'
        self.is_verified = True
        self.verification_date = timezone.now()
        self.verified_by = verified_by
        self.review_notes = notes
        self.save()
    
    def reject(self, verified_by, reason, notes=''):
        """Reject the document"""
        self.status = 'rejected'
        self.is_verified = False
        self.verified_by = verified_by
        self.rejection_reason = reason
        self.review_notes = notes
        self.save()
    
    def mark_expired(self):
        """Mark document as expired"""
        self.status = 'expired'
        self.save()


class DocumentVersion(TimeStampedModel):
    """Document version history"""
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to=user_document_path)
    uploaded_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='uploaded_document_versions'
    )
    change_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Document Version'
        verbose_name_plural = 'Document Versions'
        ordering = ['-version_number']
        unique_together = ['document', 'version_number']
    
    def __str__(self):
        return f"{self.document.name} v{self.version_number}"


class DocumentShare(TimeStampedModel):
    """Document sharing model"""
    
    ACCESS_TYPES = (
        ('view', 'View Only'),
        ('download', 'View and Download'),
    )
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='shares'
    )
    shared_with = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='shared_documents'
    )
    shared_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='documents_shared'
    )
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPES, default='view')
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Access tracking
    access_count = models.PositiveIntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Document Share'
        verbose_name_plural = 'Document Shares'
        unique_together = ['document', 'shared_with']
    
    def __str__(self):
        return f"{self.document.name} shared with {self.shared_with.get_full_name()}"
    
    @property
    def is_expired(self):
        """Check if share is expired"""
        if self.expires_at:
            return self.expires_at < timezone.now()
        return False
    
    def record_access(self):
        """Record document access"""
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed'])


class DocumentAuditLog(TimeStampedModel):
    """Document audit log"""
    
    ACTION_TYPES = (
        ('uploaded', 'Uploaded'),
        ('viewed', 'Viewed'),
        ('downloaded', 'Downloaded'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('deleted', 'Deleted'),
        ('shared', 'Shared'),
        ('updated', 'Updated'),
    )
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField(blank=True)
    
    # Technical details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    additional_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Document Audit Log'
        verbose_name_plural = 'Document Audit Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document.name} - {self.get_action_display()}"


class DocumentTemplate(TimeStampedModel):
    """Document templates for generating standard documents"""
    
    TEMPLATE_TYPES = (
        ('rental_checklist', 'Rental Checklist'),
        ('damage_report', 'Damage Report'),
        ('inspection_form', 'Inspection Form'),
        ('handover_form', 'Handover Form'),
        ('incident_report', 'Incident Report'),
    )
    
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    description = models.TextField(blank=True)
    template_content = models.JSONField(
        default=dict,
        help_text="Template structure and fields"
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Document Template'
        verbose_name_plural = 'Document Templates'
        ordering = ['template_type', 'name']
    
    def __str__(self):
        return self.name
    
    def generate_document(self, user, context=None):
        """Generate document from template"""
        if not context:
            context = {}
        
        # Implementation would depend on specific template structure
        # This is a placeholder for template processing logic
        pass
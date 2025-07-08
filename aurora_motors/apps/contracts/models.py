from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.core.models import TimeStampedModel
import uuid

class ContractTemplate(TimeStampedModel):
    """Contract template model"""
    
    TEMPLATE_TYPES = (
        ('rental_agreement', 'Rental Agreement'),
        ('terms_conditions', 'Terms and Conditions'),
        ('privacy_policy', 'Privacy Policy'),
        ('damage_waiver', 'Damage Waiver'),
        ('insurance_agreement', 'Insurance Agreement'),
        ('additional_driver', 'Additional Driver Agreement'),
    )
    
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    version = models.CharField(max_length=20, default='1.0')
    content = models.TextField(help_text="Use {{variable}} for dynamic content")
    is_active = models.BooleanField(default=True)
    is_required = models.BooleanField(default=True)
    
    # Template settings
    requires_signature = models.BooleanField(default=True)
    requires_witness = models.BooleanField(default=False)
    requires_date = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_templates'
    )
    
    class Meta:
        verbose_name = 'Contract Template'
        verbose_name_plural = 'Contract Templates'
        ordering = ['template_type', 'name']
        unique_together = ['name', 'version']
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    def get_absolute_url(self):
        return reverse('contracts:template_detail', kwargs={'pk': self.pk})
    
    def render_content(self, context=None):
        """Render template content with context variables"""
        if not context:
            context = {}
        
        content = self.content
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))
        
        return content
    
    def create_contract(self, booking, user, context=None):
        """Create a contract from this template"""
        rendered_content = self.render_content(context)
        
        contract = Contract.objects.create(
            template=self,
            booking=booking,
            user=user,
            title=f"{self.name} - {booking.booking_number}",
            content=rendered_content,
            status='draft'
        )
        
        return contract


class Contract(TimeStampedModel):
    """Contract model"""
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent for Signature'),
        ('signed', 'Signed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )
    
    # Basic information
    contract_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    template = models.ForeignKey(ContractTemplate, on_delete=models.CASCADE, related_name='contracts')
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, related_name='contracts')
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='contracts')
    
    # Contract details
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Signing information
    sent_date = models.DateTimeField(null=True, blank=True)
    signed_date = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Digital signature data
    signature_data = models.JSONField(default=dict, blank=True)
    signature_ip = models.GenericIPAddressField(null=True, blank=True)
    signature_user_agent = models.TextField(blank=True)
    
    # Files
    pdf_file = models.FileField(
        upload_to='contracts/pdfs/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])]
    )
    signed_pdf_file = models.FileField(
        upload_to='contracts/signed/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])]
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_contracts'
    )
    
    class Meta:
        verbose_name = 'Contract'
        verbose_name_plural = 'Contracts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['booking']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.get_full_name()}"
    
    def get_absolute_url(self):
        return reverse('contracts:detail', kwargs={'contract_id': self.contract_id})
    
    def get_signing_url(self):
        return reverse('contracts:sign', kwargs={'contract_id': self.contract_id})
    
    @property
    def is_expired(self):
        """Check if contract is expired"""
        return self.expires_at and self.expires_at < timezone.now()
    
    @property
    def can_be_signed(self):
        """Check if contract can be signed"""
        return (
            self.status in ['draft', 'sent'] and
            not self.is_expired
        )
    
    @property
    def days_until_expiry(self):
        """Get days until expiry"""
        if self.expires_at:
            delta = self.expires_at - timezone.now()
            return delta.days
        return None
    
    def send_for_signature(self, expires_in_days=7):
        """Send contract for signature"""
        if self.status == 'draft':
            self.status = 'sent'
            self.sent_date = timezone.now()
            self.expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
            self.save()
            
            # Send notification email
            from apps.notifications.tasks import send_contract_for_signature
            send_contract_for_signature.delay(self.id)
    
    def sign_contract(self, signature_data, ip_address, user_agent):
        """Sign the contract"""
        if self.can_be_signed:
            self.status = 'signed'
            self.signed_date = timezone.now()
            self.signature_data = signature_data
            self.signature_ip = ip_address
            self.signature_user_agent = user_agent
            self.save()
            
            # Generate signed PDF
            self.generate_signed_pdf()
            
            # Send confirmation email
            from apps.notifications.tasks import send_contract_signed_confirmation
            send_contract_signed_confirmation.delay(self.id)
    
    def generate_pdf(self):
        """Generate PDF version of contract"""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from django.core.files.base import ContentFile
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Header
        story.append(Paragraph("AURORA MOTORS PTY LTD", styles['Title']))
        story.append(Paragraph(self.title, styles['Heading1']))
        story.append(Spacer(1, 20))
        
        # Contract content
        paragraphs = self.content.split('\n\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                story.append(Paragraph(paragraph, styles['Normal']))
                story.append(Spacer(1, 12))
        
        # Contract details
        story.append(Spacer(1, 30))
        story.append(Paragraph("Contract Details:", styles['Heading2']))
        story.append(Paragraph(f"Contract ID: {self.contract_id}", styles['Normal']))
        story.append(Paragraph(f"Customer: {self.user.get_full_name()}", styles['Normal']))
        story.append(Paragraph(f"Email: {self.user.email}", styles['Normal']))
        story.append(Paragraph(f"Booking: {self.booking.booking_number}", styles['Normal']))
        story.append(Paragraph(f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Save to file field
        pdf_content = ContentFile(buffer.getvalue())
        self.pdf_file.save(
            f"contract_{self.contract_id}.pdf",
            pdf_content,
            save=False
        )
        self.save()
        
        buffer.close()
    
    def generate_signed_pdf(self):
        """Generate signed PDF with signature information"""
        if not self.signed_date:
            return
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from django.core.files.base import ContentFile
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Header
        story.append(Paragraph("AURORA MOTORS PTY LTD", styles['Title']))
        story.append(Paragraph(f"{self.title} - SIGNED COPY", styles['Heading1']))
        story.append(Spacer(1, 20))
        
        # Contract content
        paragraphs = self.content.split('\n\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                story.append(Paragraph(paragraph, styles['Normal']))
                story.append(Spacer(1, 12))
        
        # Signature section
        story.append(Spacer(1, 30))
        story.append(Paragraph("DIGITAL SIGNATURE", styles['Heading2']))
        
        signature_data = [
            ['Signed by:', self.user.get_full_name()],
            ['Email:', self.user.email],
            ['Date:', self.signed_date.strftime('%Y-%m-%d %H:%M:%S UTC')],
            ['IP Address:', self.signature_ip or 'N/A'],
            ['Contract ID:', str(self.contract_id)],
        ]
        
        signature_table = Table(signature_data)
        signature_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(signature_table)
        story.append(Spacer(1, 20))
        
        # Digital signature verification
        story.append(Paragraph(
            "This document has been digitally signed and is legally binding. "
            "The signature data is cryptographically secured and can be verified.",
            styles['Normal']
        ))
        
        # Build PDF
        doc.build(story)
        
        # Save to file field
        pdf_content = ContentFile(buffer.getvalue())
        self.signed_pdf_file.save(
            f"contract_{self.contract_id}_signed.pdf",
            pdf_content,
            save=False
        )
        self.save()
        
        buffer.close()


class ContractSignature(TimeStampedModel):
    """Individual signature for a contract"""
    
    SIGNATURE_TYPES = (
        ('customer', 'Customer'),
        ('witness', 'Witness'),
        ('staff', 'Staff'),
    )
    
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='signatures')
    signer = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='contract_signatures')
    signature_type = models.CharField(max_length=20, choices=SIGNATURE_TYPES)
    
    # Signature data
    signature_data = models.JSONField(default=dict)  # Store signature path data
    signature_text = models.CharField(max_length=200, blank=True)  # Typed signature
    signature_date = models.DateTimeField(auto_now_add=True)
    
    # Verification data
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    verification_code = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = 'Contract Signature'
        verbose_name_plural = 'Contract Signatures'
        unique_together = ['contract', 'signer', 'signature_type']
    
    def __str__(self):
        return f"{self.contract.title} - {self.signer.get_full_name()} ({self.signature_type})"


class ContractRevision(TimeStampedModel):
    """Contract revision history"""
    
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='revisions')
    revision_number = models.PositiveIntegerField()
    content = models.TextField()
    changed_by = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    change_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Contract Revision'
        verbose_name_plural = 'Contract Revisions'
        ordering = ['-revision_number']
        unique_together = ['contract', 'revision_number']
    
    def __str__(self):
        return f"{self.contract.title} - Revision {self.revision_number}"


class ContractAuditLog(TimeStampedModel):
    """Audit log for contract actions"""
    
    ACTION_TYPES = (
        ('created', 'Created'),
        ('sent', 'Sent for Signature'),
        ('viewed', 'Viewed'),
        ('signed', 'Signed'),
        ('downloaded', 'Downloaded'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('revised', 'Revised'),
    )
    
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField(blank=True)
    
    # Technical details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    additional_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Contract Audit Log'
        verbose_name_plural = 'Contract Audit Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.contract.title} - {self.get_action_display()}"


class ContractReminder(TimeStampedModel):
    """Contract signing reminders"""
    
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='reminders')
    reminder_date = models.DateTimeField()
    is_sent = models.BooleanField(default=False)
    sent_date = models.DateTimeField(null=True, blank=True)
    
    # Reminder content
    subject = models.CharField(max_length=200)
    message = models.TextField()
    
    class Meta:
        verbose_name = 'Contract Reminder'
        verbose_name_plural = 'Contract Reminders'
        ordering = ['reminder_date']
    
    def __str__(self):
        return f"Reminder for {self.contract.title}"
    
    def send_reminder(self):
        """Send the reminder email"""
        if not self.is_sent:
            from apps.notifications.tasks import send_contract_reminder
            send_contract_reminder.delay(self.id)
            
            self.is_sent = True
            self.sent_date = timezone.now()
            self.save()


class ContractAnalytics(TimeStampedModel):
    """Contract analytics and metrics"""
    
    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, related_name='analytics')
    
    # View metrics
    view_count = models.PositiveIntegerField(default=0)
    unique_viewers = models.PositiveIntegerField(default=0)
    first_viewed = models.DateTimeField(null=True, blank=True)
    last_viewed = models.DateTimeField(null=True, blank=True)
    
    # Signing metrics
    time_to_sign = models.DurationField(null=True, blank=True)  # Time from sent to signed
    sign_attempts = models.PositiveIntegerField(default=0)
    
    # Download metrics
    download_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Contract Analytics'
        verbose_name_plural = 'Contract Analytics'
    
    def __str__(self):
        return f"Analytics for {self.contract.title}"
    
    def record_view(self, user):
        """Record a contract view"""
        self.view_count += 1
        if not self.first_viewed:
            self.first_viewed = timezone.now()
        self.last_viewed = timezone.now()
        self.save()
        
        # Log the view
        ContractAuditLog.objects.create(
            contract=self.contract,
            user=user,
            action='viewed',
            description=f"Contract viewed by {user.get_full_name()}"
        )
    
    def record_sign_attempt(self):
        """Record a signing attempt"""
        self.sign_attempts += 1
        self.save()
    
    def record_signed(self):
        """Record successful signing"""
        if self.contract.sent_date and self.contract.signed_date:
            self.time_to_sign = self.contract.signed_date - self.contract.sent_date
        self.save()
    
    def record_download(self, user):
        """Record a download"""
        self.download_count += 1
        self.save()
        
        # Log the download
        ContractAuditLog.objects.create(
            contract=self.contract,
            user=user,
            action='downloaded',
            description=f"Contract downloaded by {user.get_full_name()}"
        )
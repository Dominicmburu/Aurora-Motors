from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Document, DocumentAuditLog

@shared_task
def check_expired_documents():
    """Check and mark expired documents"""
    
    today = timezone.now().date()
    expired_documents = Document.objects.filter(
        expiry_date__lt=today,
        status='approved'
    )
    
    updated_count = 0
    for document in expired_documents:
        document.mark_expired()
        
        # Create audit log
        DocumentAuditLog.objects.create(
            document=document,
            action='expired',
            description='Document expired automatically'
        )
        
        updated_count += 1
    
    return f"Marked {updated_count} documents as expired"

@shared_task
def send_expiry_notifications():
    """Send notifications for documents expiring soon"""
    
    # Get documents expiring in 7 days
    warning_date = timezone.now().date() + timezone.timedelta(days=7)
    expiring_documents = Document.objects.filter(
        expiry_date=warning_date,
        status='approved'
    ).select_related('user')
    
    sent_count = 0
    for document in expiring_documents:
        try:
            # Send notification email
            subject = f"Document Expiring Soon: {document.name}"
            message = render_to_string('documents/emails/expiry_warning.txt', {
                'document': document,
                'user': document.user,
            })
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[document.user.email],
                fail_silently=False,
            )
            
            sent_count += 1
            
        except Exception as e:
            # Log error but continue with other notifications
            print(f"Failed to send expiry notification for document {document.id}: {e}")
    
    return f"Sent {sent_count} expiry notifications"

@shared_task
def cleanup_old_document_versions():
    """Cleanup old document versions (keep last 5 versions)"""
    
    from .models import DocumentVersion
    
    # Get documents with more than 5 versions
    documents_with_versions = Document.objects.annotate(
        version_count=models.Count('versions')
    ).filter(version_count__gt=5)
    
    deleted_count = 0
    for document in documents_with_versions:
        # Keep only the latest 5 versions
        versions_to_delete = document.versions.all()[5:]
        
        for version in versions_to_delete:
            # Delete the file
            if version.file:
                version.file.delete()
            
            # Delete the version record
            version.delete()
            deleted_count += 1
    
    return f"Cleaned up {deleted_count} old document versions"

@shared_task
def generate_document_report():
    """Generate monthly document statistics report"""
    
    from django.db.models import Count
    from datetime import timedelta
    
    # Get data for the last month
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    documents = Document.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    stats = {
        'total_documents': documents.count(),
        'approved_documents': documents.filter(status='approved').count(),
        'rejected_documents': documents.filter(status='rejected').count(),
        'pending_documents': documents.filter(status='pending').count(),
        'by_type': {},
        'by_category': {},
    }
    
    # Documents by type
    type_data = documents.values('document_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    for item in type_data:
        stats['by_type'][item['document_type']] = item['count']
    
    # Documents by category
    category_data = documents.filter(category__isnull=False).values(
        'category__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    for item in category_data:
        stats['by_category'][item['category__name']] = item['count']
    
    # Send report to admin
    from apps.accounts.models import CustomUser
    admin_emails = [
        user.email for user in 
        CustomUser.objects.filter(is_staff=True, is_active=True)
    ]
    
    if admin_emails:
        subject = f"Document Management Report - {start_date} to {end_date}"
        message = render_to_string('documents/emails/monthly_report.txt', {
            'stats': stats,
            'start_date': start_date,
            'end_date': end_date,
        })
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=True,
        )
    
    return f"Generated document report: {stats}"

@shared_task
def process_document_queue():
    """Process pending document reviews"""
    
    # Get documents pending review for more than 24 hours
    cutoff_time = timezone.now() - timezone.timedelta(hours=24)
    old_pending = Document.objects.filter(
        status='pending',
        created_at__lt=cutoff_time
    ).select_related('user')
    
    # Send reminder to staff
    if old_pending.exists():
        from apps.accounts.models import CustomUser
        staff_emails = [
            user.email for user in 
            CustomUser.objects.filter(
                is_staff=True, 
                is_active=True,
                user_type__in=['staff', 'admin']
            )
        ]
        
        if staff_emails:
            subject = f"Pending Document Reviews - {old_pending.count()} documents"
            message = render_to_string('documents/emails/review_reminder.txt', {
                'documents': old_pending[:10],  # Limit to first 10
                'total_count': old_pending.count(),
            })
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=staff_emails,
                fail_silently=True,
            )
    
    return f"Processed document queue - {old_pending.count()} pending reviews"
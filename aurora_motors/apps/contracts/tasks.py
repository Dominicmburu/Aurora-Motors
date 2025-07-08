from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Contract, ContractReminder

@shared_task
def send_contract_signing_reminders():
    """Send reminders for unsigned contracts"""
    
    # Get reminders that need to be sent
    now = timezone.now()
    pending_reminders = ContractReminder.objects.filter(
        reminder_date__lte=now,
        is_sent=False,
        contract__status='sent'
    )
    
    sent_count = 0
    for reminder in pending_reminders:
        try:
            # Send reminder email
            send_mail(
                subject=reminder.subject,
                message=reminder.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reminder.contract.user.email],
                fail_silently=False,
            )
            
            # Mark as sent
            reminder.is_sent = True
            reminder.sent_date = now
            reminder.save()
            
            sent_count += 1
            
        except Exception as e:
            # Log error but continue with other reminders
            print(f"Failed to send reminder for contract {reminder.contract.contract_id}: {e}")
    
    return f"Sent {sent_count} contract reminders"

@shared_task
def check_expired_contracts():
    """Mark expired contracts"""
    
    now = timezone.now()
    expired_contracts = Contract.objects.filter(
        status='sent',
        expires_at__lt=now
    )
    
    updated_count = 0
    for contract in expired_contracts:
        contract.status = 'expired'
        contract.save()
        
        # Create audit log
        from .models import ContractAuditLog
        ContractAuditLog.objects.create(
            contract=contract,
            action='expired',
            description='Contract expired automatically'
        )
        
        updated_count += 1
    
    return f"Marked {updated_count} contracts as expired"

@shared_task
def generate_contract_analytics_report():
    """Generate monthly contract analytics report"""
    
    from django.db.models import Count, Avg
    from datetime import timedelta
    
    # Get data for the last month
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    contracts = Contract.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    stats = {
        'total_contracts': contracts.count(),
        'signed_contracts': contracts.filter(status='signed').count(),
        'expired_contracts': contracts.filter(status='expired').count(),
        'signing_rate': 0,
        'average_signing_time': 0,
    }
    
    # Calculate signing rate
    sent_contracts = contracts.filter(status__in=['sent', 'signed', 'expired'])
    if sent_contracts.count() > 0:
        signed_count = contracts.filter(status='signed').count()
        stats['signing_rate'] = (signed_count / sent_contracts.count()) * 100
    
    # Calculate average signing time
    signed_contracts = contracts.filter(
        status='signed',
        sent_date__isnull=False,
        signed_date__isnull=False
    )
    
    if signed_contracts.exists():
        total_time = sum([
            (contract.signed_date - contract.sent_date).total_seconds()
            for contract in signed_contracts
        ])
        average_seconds = total_time / signed_contracts.count()
        stats['average_signing_time'] = average_seconds / 3600  # Convert to hours
    
    # Send report to admin
    admin_emails = [
        user.email for user in 
        settings.AUTH_USER_MODEL.objects.filter(is_staff=True, is_active=True)
    ]
    
    if admin_emails:
        subject = f"Contract Analytics Report - {start_date} to {end_date}"
        message = render_to_string('contracts/emails/analytics_report.txt', {
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
    
    return f"Generated analytics report: {stats}"
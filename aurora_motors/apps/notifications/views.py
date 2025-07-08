from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Avg
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import user_passes_test
import json

from .models import (
    NotificationTemplate, Notification, NotificationPreference,
    NotificationChannel, NotificationLog, NotificationQueue
)
from .forms import (
    NotificationTemplateForm, NotificationPreferenceForm, NotificationChannelForm,
    BulkNotificationForm, NotificationTestForm, NotificationSearchForm
)
from apps.accounts.permissions import StaffRequiredMixin


class NotificationListView(LoginRequiredMixin, ListView):
    """User notification list view"""
    
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('template').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add user notification statistics
        user_notifications = self.get_queryset()
        context['stats'] = {
            'total': user_notifications.count(),
            'unread': user_notifications.exclude(status='read').count(),
            'pending': user_notifications.filter(status='pending').count(),
            'failed': user_notifications.filter(status='failed').count(),
        }
        
        return context


class NotificationDetailView(LoginRequiredMixin, DetailView):
    """Notification detail view"""
    
    model = Notification
    template_name = 'notifications/notification_detail.html'
    context_object_name = 'notification'
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('template')
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        
        # Mark notification as read
        if self.object.status != 'read':
            self.object.mark_read()
        
        return response


class NotificationPreferenceView(LoginRequiredMixin, UpdateView):
    """User notification preferences"""
    
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = 'notifications/preferences.html'
    success_url = reverse_lazy('notifications:preferences')
    
    def get_object(self):
        """Get or create notification preferences for user"""
        preferences, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferences
    
    def form_valid(self, form):
        messages.success(self.request, 'Notification preferences updated successfully!')
        return super().form_valid(form)


# Staff/Admin Views
class NotificationTemplateListView(StaffRequiredMixin, ListView):
    """Notification template list view"""
    
    model = NotificationTemplate
    template_name = 'notifications/template_list.html'
    context_object_name = 'templates'
    
    def get_queryset(self):
        return NotificationTemplate.objects.annotate(
            notification_count=Count('notifications')
        ).order_by('trigger_type', 'template_type')


class NotificationTemplateDetailView(StaffRequiredMixin, DetailView):
    """Notification template detail view"""
    
    model = NotificationTemplate
    template_name = 'notifications/template_detail.html'
    context_object_name = 'template'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template = self.object
        
        # Get recent notifications using this template
        context['recent_notifications'] = Notification.objects.filter(
            template=template
        ).select_related('recipient')[:10]
        
        # Get template statistics
        notifications = Notification.objects.filter(template=template)
        context['stats'] = {
            'total_sent': notifications.count(),
            'delivered': notifications.filter(status='delivered').count(),
            'failed': notifications.filter(status='failed').count(),
            'read': notifications.filter(status='read').count(),
        }
        
        return context


class NotificationTemplateCreateView(StaffRequiredMixin, CreateView):
    """Create notification template"""
    
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = 'notifications/template_form.html'
    success_url = reverse_lazy('notifications:template_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Notification template created successfully!')
        return super().form_valid(form)


class NotificationTemplateUpdateView(StaffRequiredMixin, UpdateView):
    """Update notification template"""
    
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = 'notifications/template_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Notification template updated successfully!')
        return super().form_valid(form)


class NotificationChannelListView(StaffRequiredMixin, ListView):
    """Notification channel list view"""
    
    model = NotificationChannel
    template_name = 'notifications/channel_list.html'
    context_object_name = 'channels'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add channel statistics
        for channel in context['channels']:
            channel.success_rate = channel.delivery_rate
        
        return context


class NotificationChannelCreateView(StaffRequiredMixin, CreateView):
    """Create notification channel"""
    
    model = NotificationChannel
    form_class = NotificationChannelForm
    template_name = 'notifications/channel_form.html'
    success_url = reverse_lazy('notifications:channel_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Notification channel created successfully!')
        return super().form_valid(form)


class NotificationChannelUpdateView(StaffRequiredMixin, UpdateView):
    """Update notification channel"""
    
    model = NotificationChannel
    form_class = NotificationChannelForm
    template_name = 'notifications/channel_form.html'
    success_url = reverse_lazy('notifications:channel_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Notification channel updated successfully!')
        return super().form_valid(form)


class NotificationManagementView(StaffRequiredMixin, ListView):
    """Notification management dashboard for staff"""
    
    model = Notification
    template_name = 'notifications/management.html'
    context_object_name = 'notifications'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Notification.objects.select_related(
            'template', 'recipient'
        ).order_by('-created_at')
        
        # Apply search filters
        self.search_form = NotificationSearchForm(self.request.GET)
        if self.search_form.is_valid():
            search = self.search_form.cleaned_data.get('search')
            status = self.search_form.cleaned_data.get('status')
            template_type = self.search_form.cleaned_data.get('template_type')
            priority = self.search_form.cleaned_data.get('priority')
            date_from = self.search_form.cleaned_data.get('date_from')
            date_to = self.search_form.cleaned_data.get('date_to')
            
            if search:
                queryset = queryset.filter(
                    Q(subject__icontains=search) |
                    Q(body__icontains=search) |
                    Q(recipient__first_name__icontains=search) |
                    Q(recipient__last_name__icontains=search) |
                    Q(recipient__email__icontains=search)
                )
            
            if status:
                queryset = queryset.filter(status=status)
            
            if template_type:
                queryset = queryset.filter(template__template_type=template_type)
            
            if priority:
                queryset = queryset.filter(priority=priority)
            
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = getattr(self, 'search_form', NotificationSearchForm())
        
        # Add statistics
        today = timezone.now().date()
        context['stats'] = {
            'total_today': Notification.objects.filter(created_at__date=today).count(),
            'sent_today': Notification.objects.filter(
                sent_at__date=today
            ).count(),
            'failed_today': Notification.objects.filter(
                status='failed',
                created_at__date=today
            ).count(),
            'pending_queue': NotificationQueue.objects.filter(
                is_processing=False
            ).count(),
        }
        
        return context


@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def bulk_notification_send(request):
    """Send bulk notifications"""
    
    if request.method == 'POST':
        from apps.accounts.models import CustomUser
        recipients_queryset = CustomUser.objects.filter(is_active=True)
        form = BulkNotificationForm(request.POST, recipients_queryset=recipients_queryset)
        
        if form.is_valid():
            template = form.cleaned_data['template']
            recipients = form.cleaned_data['recipients']
            send_immediately = form.cleaned_data['send_immediately']
            scheduled_at = form.cleaned_data['scheduled_at']
            
            created_count = 0
            
            for recipient in recipients:
                # Check user preferences
                preferences, _ = NotificationPreference.objects.get_or_create(user=recipient)
                if not preferences.should_send_notification(template):
                    continue
                
                # Create notification
                from .tasks import create_notification
                create_notification.delay(
                    template_id=template.id,
                    recipient_id=recipient.id,
                    scheduled_at=scheduled_at.isoformat() if scheduled_at else None,
                    context={}
                )
                created_count += 1
            
            messages.success(
                request,
                f'{created_count} notifications created successfully!'
            )
            return redirect('notifications:management')
    else:
        from apps.accounts.models import CustomUser
        recipients_queryset = CustomUser.objects.filter(is_active=True)
        form = BulkNotificationForm(recipients_queryset=recipients_queryset)
    
    return render(request, 'notifications/bulk_send.html', {
        'form': form
    })


@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def test_notification(request):
    """Test notification template"""
    
    if request.method == 'POST':
        form = NotificationTestForm(request.POST)
        if form.is_valid():
            template = form.cleaned_data['template']
            test_recipient = form.cleaned_data['test_recipient']
            
            # Build test context
            context = {
                'user_name': form.cleaned_data['user_name'],
                'booking_number': form.cleaned_data['booking_number'],
                'vehicle_name': form.cleaned_data['vehicle_name'],
                'total_amount': form.cleaned_data['total_amount'],
                'company_name': 'Aurora Motors Pty Ltd',
                'site_url': request.build_absolute_uri('/'),
            }
            
            # Send test notification
            from .tasks import send_test_notification
            send_test_notification.delay(
                template_id=template.id,
                test_email=test_recipient,
                context=context
            )
            
            messages.success(
                request,
                f'Test notification sent to {test_recipient}!'
            )
            return redirect('notifications:test')
    else:
        form = NotificationTestForm()

    return render(request, 'notifications/test.html', {
        'form': form
    })


# AJAX Views
@require_http_methods(["GET"])
@login_required
def get_unread_notifications(request):
    """Get unread notifications for user (AJAX)"""
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        status__in=['sent', 'delivered']
    ).select_related('template').order_by('-created_at')[:10]
    
    notification_list = []
    for notification in notifications:
        notification_list.append({
            'id': notification.id,
            'title': notification.title or notification.template.name,
            'body': notification.body[:100] + '...' if len(notification.body) > 100 else notification.body,
            'created_at': notification.created_at.isoformat(),
            'url': reverse('notifications:detail', kwargs={'pk': notification.pk})
        })
    
    return JsonResponse({
        'notifications': notification_list,
        'unread_count': notifications.count()
    })


@require_http_methods(["POST"])
@login_required
def mark_notification_read(request, pk):
    """Mark notification as read (AJAX)"""
    
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user
    )
    
    notification.mark_read()
    
    return JsonResponse({
        'success': True,
        'message': 'Notification marked as read'
    })


@require_http_methods(["POST"])
@login_required
def mark_all_read(request):
    """Mark all notifications as read (AJAX)"""
    
    updated = Notification.objects.filter(
        recipient=request.user,
        status__in=['sent', 'delivered']
    ).update(status='read', read_at=timezone.now())
    
    return JsonResponse({
        'success': True,
        'message': f'{updated} notifications marked as read'
    })


@require_http_methods(["GET"])
@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def notification_statistics(request):
    """Get notification statistics (AJAX)"""
    
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timezone.timedelta(days=days)
    
    notifications = Notification.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    stats = {
        'total_notifications': notifications.count(),
        'sent_notifications': notifications.filter(status__in=['sent', 'delivered', 'read']).count(),
        'failed_notifications': notifications.filter(status='failed').count(),
        'pending_notifications': notifications.filter(status='pending').count(),
        'by_template_type': {},
        'by_status': {},
        'delivery_trend': [],
        'top_templates': [],
    }
    
    # Notifications by template type
    type_data = notifications.values(
        'template__template_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    for item in type_data:
        template_type = item['template__template_type']
        stats['by_template_type'][template_type] = item['count']
    
    # Notifications by status
    status_data = notifications.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    for item in status_data:
        stats['by_status'][item['status']] = item['count']
    
    # Daily delivery trend
    from django.db.models.functions import TruncDate
    daily_data = notifications.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Count('id'),
        sent=Count('id', filter=Q(status__in=['sent', 'delivered', 'read'])),
        failed=Count('id', filter=Q(status='failed'))
    ).order_by('date')
    
    for item in daily_data:
        stats['delivery_trend'].append({
            'date': item['date'].isoformat(),
            'total': item['total'],
            'sent': item['sent'],
            'failed': item['failed']
        })
    
    # Top templates
    template_data = notifications.values(
        'template__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    for item in template_data:
        stats['top_templates'].append({
            'name': item['template__name'],
            'count': item['count']
        })
    
    return JsonResponse(stats)


@require_http_methods(["GET"])
@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def queue_status(request):
    """Get notification queue status (AJAX)"""
    
    queue_stats = {
        'immediate': NotificationQueue.objects.filter(
            queue_type='immediate',
            is_processing=False
        ).count(),
        'high': NotificationQueue.objects.filter(
            queue_type='high',
            is_processing=False
        ).count(),
        'normal': NotificationQueue.objects.filter(
            queue_type='normal',
            is_processing=False
        ).count(),
        'low': NotificationQueue.objects.filter(
            queue_type='low',
            is_processing=False
        ).count(),
        'digest': NotificationQueue.objects.filter(
            queue_type='digest',
            is_processing=False
        ).count(),
        'processing': NotificationQueue.objects.filter(
            is_processing=True
        ).count(),
    }
    
    # Recent queue activity
    recent_notifications = Notification.objects.filter(
        status__in=['sent', 'delivered', 'failed']
    ).order_by('-sent_at')[:10]
    
    recent_activity = []
    for notification in recent_notifications:
        recent_activity.append({
            'id': notification.id,
            'template': notification.template.name,
            'recipient': notification.recipient.get_full_name(),
            'status': notification.status,
            'sent_at': notification.sent_at.isoformat() if notification.sent_at else None
        })
    
    return JsonResponse({
        'queue_stats': queue_stats,
        'recent_activity': recent_activity,
        'total_pending': sum([
            queue_stats['immediate'],
            queue_stats['high'],
            queue_stats['normal'],
            queue_stats['low'],
            queue_stats['digest']
        ])
    })


# Dashboard view
class NotificationDashboardView(StaffRequiredMixin, TemplateView):
    """Notification system dashboard"""
    
    template_name = 'notifications/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        today = timezone.now().date()
        
        # Today's statistics
        context['notifications_sent_today'] = Notification.objects.filter(
            sent_at__date=today
        ).count()
        
        context['notifications_failed_today'] = Notification.objects.filter(
            status='failed',
            created_at__date=today
        ).count()
        
        # Queue statistics
        context['queue_pending'] = NotificationQueue.objects.filter(
            is_processing=False
        ).count()
        
        context['queue_processing'] = NotificationQueue.objects.filter(
            is_processing=True
        ).count()
        
        # Recent notifications
        context['recent_notifications'] = Notification.objects.select_related(
            'template', 'recipient'
        ).order_by('-created_at')[:10]
        
        # Failed notifications requiring attention
        context['failed_notifications'] = Notification.objects.filter(
            status='failed',
            retry_count__gte=3
        ).select_related('template', 'recipient')[:10]
        
        # Template performance
        context['template_performance'] = NotificationTemplate.objects.annotate(
            total_sent=Count('notifications'),
            success_rate=Count('notifications', filter=Q(
                notifications__status__in=['sent', 'delivered', 'read']
            )) * 100.0 / Count('notifications')
        ).filter(total_sent__gt=0).order_by('-total_sent')[:5]
        
        # Channel performance
        context['channel_performance'] = NotificationChannel.objects.filter(
            is_active=True
        ).order_by('-total_sent')[:5]
        
        return context

        

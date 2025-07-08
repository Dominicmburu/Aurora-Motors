from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy, reverse
from django.db.models.functions import TruncDate
from django.db.models import Q, Count, Sum, Avg, F
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import user_passes_test
from datetime import datetime, timedelta
import json

from .models import AnalyticsEvent, Report, Dashboard, KPI, Metric
from .forms import ReportForm, DashboardForm, KPIForm, AnalyticsFilterForm, CustomReportForm
from .utils import ReportGenerator, KPICalculator, ChartDataBuilder
from apps.accounts.permissions import StaffRequiredMixin
from apps.bookings.models import Booking
from apps.vehicles.models import Vehicle
from apps.accounts.models import CustomUser


class AnalyticsDashboardView(StaffRequiredMixin, TemplateView):
    """Main analytics dashboard"""
    
    template_name = 'analytics/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date ranges
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Key metrics
        context['total_users'] = CustomUser.objects.filter(is_active=True).count()
        context['total_bookings'] = Booking.objects.count()
        context['total_vehicles'] = Vehicle.objects.filter(is_active=True).count()
        context['active_bookings'] = Booking.objects.filter(status='active').count()
        
        # Recent activity
        context['recent_bookings'] = Booking.objects.select_related(
            'user', 'vehicle'
        ).order_by('-created_at')[:5]
        
        # Booking trends
        booking_trend = []
        for i in range(7):
            date = today - timedelta(days=i)
            count = Booking.objects.filter(created_at__date=date).count()
            booking_trend.append({
                'date': date.isoformat(),
                'count': count
            })
        context['booking_trend'] = list(reversed(booking_trend))
        
        # Revenue data
        revenue_data = Booking.objects.filter(
            created_at__date__gte=month_ago,
            status__in=['confirmed', 'active', 'completed']
        ).aggregate(
            total_revenue=Sum('total_amount'),
            avg_booking_value=Avg('total_amount')
        )
        context['total_revenue'] = revenue_data['total_revenue'] or 0
        context['avg_booking_value'] = revenue_data['avg_booking_value'] or 0
        
        # Top vehicles
        context['top_vehicles'] = Vehicle.objects.annotate(
            booking_count=Count('bookings')
        ).order_by('-booking_count')[:5]
        
        # User activity
        context['new_users_this_week'] = CustomUser.objects.filter(
            date_joined__date__gte=week_ago
        ).count()
        
        # System health metrics
        context['system_health'] = {
            'active_users': CustomUser.objects.filter(
                last_login__date__gte=week_ago
            ).count(),
            'pending_documents': self.get_pending_documents_count(),
            'overdue_bookings': Booking.objects.filter(
                status__in=['confirmed', 'active'],
                end_date__lt=timezone.now()
            ).count(),
        }
        
        return context
    
    def get_pending_documents_count(self):
        """Get count of pending documents"""
        try:
            from apps.documents.models import Document
            return Document.objects.filter(status='pending').count()
        except:
            return 0


class ReportListView(StaffRequiredMixin, ListView):
    """Report list view"""
    
    model = Report
    template_name = 'analytics/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Report.objects.select_related('created_by')
        
        # Filter by user access
        if not self.request.user.is_admin_user:
            queryset = queryset.filter(
                Q(created_by=self.request.user) |
                Q(is_public=True) |
                Q(shared_with=self.request.user)
            )
        
        return queryset.order_by('-created_at')


class ReportDetailView(StaffRequiredMixin, DetailView):
    """Report detail view"""
    
    model = Report
    template_name = 'analytics/report_detail.html'
    context_object_name = 'report'
    
    def get_queryset(self):
        queryset = Report.objects.select_related('created_by')
        
        # Filter by user access
        if not self.request.user.is_admin_user:
            queryset = queryset.filter(
                Q(created_by=self.request.user) |
                Q(is_public=True) |
                Q(shared_with=self.request.user)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Generate report data if not cached or outdated
        report = self.object
        if not report.data or not report.last_generated or \
           (timezone.now() - report.last_generated).total_seconds() > 3600:  # 1 hour cache
            report.generate_data()
        
        context['chart_data'] = self.build_chart_data(report)
        
        return context
    
    def build_chart_data(self, report):
        """Build chart data for visualization"""
        builder = ChartDataBuilder(report)
        return builder.build()


class ReportCreateView(StaffRequiredMixin, CreateView):
    """Create report"""
    
    model = Report
    form_class = ReportForm
    template_name = 'analytics/report_form.html'
    success_url = reverse_lazy('analytics:report_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Report created successfully!')
        return super().form_valid(form)


class ReportUpdateView(StaffRequiredMixin, UpdateView):
    """Update report"""
    
    model = Report
    form_class = ReportForm
    template_name = 'analytics/report_form.html'
    
    def get_queryset(self):
        # Users can only edit their own reports (unless admin)
        if self.request.user.is_admin_user:
            return Report.objects.all()
        return Report.objects.filter(created_by=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Report updated successfully!')
        return super().form_valid(form)


class CustomReportBuilderView(StaffRequiredMixin, TemplateView):
    """Custom report builder"""
    
    template_name = 'analytics/report_builder.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CustomReportForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = CustomReportForm(request.POST)
        if form.is_valid():
            # Generate custom report
            report_data = self.generate_custom_report(form.cleaned_data)
            return JsonResponse(report_data)
        
        return JsonResponse({'errors': form.errors}, status=400)
    
    def generate_custom_report(self, data):
        """Generate custom report based on form data"""
        from .utils import CustomReportGenerator
        
        generator = CustomReportGenerator(data)
        return generator.generate()


class KPIDashboardView(StaffRequiredMixin, TemplateView):
    """KPI dashboard"""
    
    template_name = 'analytics/kpi_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get active KPIs
        kpis = KPI.objects.filter(is_active=True).order_by('name')
        
        # Update KPI values
        for kpi in kpis:
            if not kpi.last_updated or \
               (timezone.now() - kpi.last_updated).total_seconds() > 3600:  # 1 hour
                kpi.update_value()
        
        context['kpis'] = kpis
        
        return context


class UserActivityView(StaffRequiredMixin, TemplateView):
    """User activity analytics"""
    
    template_name = 'analytics/user_activity.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter form
        filter_form = AnalyticsFilterForm(self.request.GET)
        context['filter_form'] = filter_form
        
        # Build base queryset
        events = AnalyticsEvent.objects.all()
        
        # Apply filters
        if filter_form.is_valid():
            if filter_form.cleaned_data.get('date_from'):
                events = events.filter(created_at__date__gte=filter_form.cleaned_data['date_from'])
            if filter_form.cleaned_data.get('date_to'):
                events = events.filter(created_at__date__lte=filter_form.cleaned_data['date_to'])
            if filter_form.cleaned_data.get('category'):
                events = events.filter(category=filter_form.cleaned_data['category'])
            if filter_form.cleaned_data.get('action'):
                events = events.filter(action=filter_form.cleaned_data['action'])
            if filter_form.cleaned_data.get('user_type'):
                user_type = filter_form.cleaned_data['user_type']
                events = events.filter(user__user_type=user_type)
        
        # Get statistics
        context['total_events'] = events.count()
        context['unique_users'] = events.values('user').distinct().count()
        context['unique_sessions'] = events.values('session_key').distinct().count()
        
        # Top events
        context['top_events'] = events.values(
            'category', 'action'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # User activity over time
        context['activity_timeline'] = self.get_activity_timeline(events)
        
        return context
    
    def get_activity_timeline(self, events):
        """Get activity timeline data"""
        from django.db.models.functions import TruncDate
        
        timeline = events.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return [
            {
                'date': item['date'].isoformat(),
                'count': item['count']
            }
            for item in timeline
        ]


# AJAX Views
@require_http_methods(["GET"])
@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def booking_analytics_data(request):
    """Get booking analytics data"""
    
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    bookings = Booking.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    # Basic statistics
    stats = {
        'total_bookings': bookings.count(),
        'confirmed_bookings': bookings.filter(status='confirmed').count(),
        'active_bookings': bookings.filter(status='active').count(),
        'completed_bookings': bookings.filter(status='completed').count(),
        'cancelled_bookings': bookings.filter(status='cancelled').count(),
        'total_revenue': float(bookings.aggregate(
            total=Sum('total_amount')
        )['total'] or 0),
        'average_booking_value': float(bookings.aggregate(
            avg=Avg('total_amount')
        )['avg'] or 0),
    }
    
    # Daily booking trend
    from django.db.models.functions import TruncDate
    daily_data = bookings.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('date')
    
    stats['daily_trend'] = [
        {
            'date': item['date'].isoformat(),
            'bookings': item['count'],
            'revenue': float(item['revenue'] or 0)
        }
        for item in daily_data
    ]
    
    # Booking status distribution
    status_data = bookings.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    stats['status_distribution'] = [
        {
            'status': item['status'],
            'count': item['count']
        }
        for item in status_data
    ]
    
    # Top vehicles
    vehicle_data = bookings.values(
        'vehicle__name', 'vehicle__brand__name'
    ).annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('-count')[:5]
    
    stats['top_vehicles'] = [
        {
            'vehicle': f"{item['vehicle__brand__name']} {item['vehicle__name']}",
            'bookings': item['count'],
            'revenue': float(item['revenue'] or 0)
        }
        for item in vehicle_data
    ]
    
    return JsonResponse(stats)


@require_http_methods(["GET"])
@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def vehicle_utilization_data(request):
    """Get vehicle utilization data"""
    
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    vehicles = Vehicle.objects.filter(is_active=True).annotate(
        booking_count=Count('bookings', filter=Q(
            bookings__created_at__date__range=[start_date, end_date]
        )),
        total_days_booked=Sum('bookings__total_days', filter=Q(
            bookings__created_at__date__range=[start_date, end_date],
            bookings__status__in=['confirmed', 'active', 'completed']
        )),
        revenue=Sum('bookings__total_amount', filter=Q(
            bookings__created_at__date__range=[start_date, end_date],
            bookings__status__in=['confirmed', 'active', 'completed']
        ))
    ).order_by('-booking_count')
    
    utilization_data = []
    for vehicle in vehicles:
        # Calculate utilization percentage
        total_available_days = days
        booked_days = vehicle.total_days_booked or 0
        utilization_rate = (booked_days / total_available_days) * 100 if total_available_days > 0 else 0
        
        utilization_data.append({
            'vehicle_name': f"{vehicle.brand.name} {vehicle.name}",
            'booking_count': vehicle.booking_count,
            'total_days_booked': booked_days,
            'utilization_rate': round(utilization_rate, 1),
            'revenue': float(vehicle.revenue or 0)
        })
    
    return JsonResponse({
        'vehicles': utilization_data,
        'period_days': days
    })


@require_http_methods(["GET"])
@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def revenue_analytics_data(request):
    """Get revenue analytics data"""
    
    period = request.GET.get('period', 'month')  # day, week, month, year
    
    if period == 'day':
        days_back = 30
        trunc_func = TruncDate
    elif period == 'week':
        days_back = 84  # 12 weeks
        from django.db.models.functions import TruncWeek
        trunc_func = TruncWeek
    elif period == 'month':
        days_back = 365  # 12 months
        from django.db.models.functions import TruncMonth
        trunc_func = TruncMonth
    else:  # year
        days_back = 1825  # 5 years
        from django.db.models.functions import TruncYear
        trunc_func = TruncYear
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    bookings = Booking.objects.filter(
        created_at__date__range=[start_date, end_date],
        status__in=['confirmed', 'active', 'completed']
    )
    
    # Revenue over time
    revenue_data = bookings.annotate(
        period=trunc_func('created_at')
    ).values('period').annotate(
        revenue=Sum('total_amount'),
        booking_count=Count('id')
    ).order_by('period')
    
    revenue_trend = [
        {
            'period': item['period'].isoformat(),
            'revenue': float(item['revenue'] or 0),
            'bookings': item['booking_count']
        }
        for item in revenue_data
    ]
    
    # Summary statistics
    total_revenue = bookings.aggregate(total=Sum('total_amount'))['total'] or 0
    avg_booking_value = bookings.aggregate(avg=Avg('total_amount'))['avg'] or 0
    
    # Revenue by vehicle category
    category_revenue = bookings.values(
        'vehicle__category__name'
    ).annotate(
        revenue=Sum('total_amount'),
        count=Count('id')
    ).order_by('-revenue')
    
    return JsonResponse({
        'revenue_trend': revenue_trend,
        'total_revenue': float(total_revenue),
        'avg_booking_value': float(avg_booking_value),
        'category_breakdown': [
            {
                'category': item['vehicle__category__name'],
                'revenue': float(item['revenue'] or 0),
                'bookings': item['count']
            }
            for item in category_revenue
        ],
        'period': period
    })


@require_http_methods(["POST"])
@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def generate_report(request, pk):
    """Generate report data"""
    
    report = get_object_or_404(Report, pk=pk)
    
    # Check access permissions
    if not (report.created_by == request.user or 
            report.is_public or 
            request.user in report.shared_with.all() or
            request.user.is_admin_user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = report.generate_data()
        return JsonResponse({
            'success': True,
            'data': data,
            'last_generated': report.last_generated.isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
@login_required
def track_event(request):
    """Track analytics event"""
    
    try:
        data = json.loads(request.body)
        
        event = AnalyticsEvent.objects.create(
            category=data.get('category'),
            action=data.get('action'),
            label=data.get('label', ''),
            value=data.get('value'),
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referer=request.META.get('HTTP_REFERER', ''),
            path=data.get('path', ''),
            properties=data.get('properties', {})
        )
        
        return JsonResponse({'success': True, 'event_id': event.id})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
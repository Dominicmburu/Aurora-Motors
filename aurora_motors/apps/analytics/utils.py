from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
import json

class ReportGenerator:
    """Generate report data based on report configuration"""
    
    def __init__(self, report):
        self.report = report
        self.config = report.config
        self.filters = report.filters
    
    def generate(self):
        """Generate report data based on report type"""
        
        method_name = f"generate_{self.report.report_type}"
        if hasattr(self, method_name):
            return getattr(self, method_name)()
        else:
            return {'error': f'Unknown report type: {self.report.report_type}'}
    
    def generate_user_activity(self):
        """Generate user activity report"""
        from apps.accounts.models import CustomUser
        from .models import AnalyticsEvent
        
        # Get date range
        date_from, date_to = self.get_date_range()
        
        users = CustomUser.objects.filter(is_active=True)
        if date_from:
            users = users.filter(date_joined__gte=date_from)
        if date_to:
            users = users.filter(date_joined__lte=date_to)
        
        # User statistics
        total_users = users.count()
        new_users = users.filter(
            date_joined__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Activity events
        events = AnalyticsEvent.objects.all()
        if date_from:
            events = events.filter(created_at__date__gte=date_from)
        if date_to:
            events = events.filter(created_at__date__lte=date_to)
        
        # User type breakdown
        user_types = users.values('user_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Active users (logged in within last 30 days)
        active_users = users.filter(
            last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        return {
            'total_users': total_users,
            'new_users': new_users,
            'active_users': active_users,
            'user_types': list(user_types),
            'total_events': events.count(),
            'unique_sessions': events.values('session_key').distinct().count(),
        }
    
    def generate_booking_analytics(self):
        """Generate booking analytics report"""
        from apps.bookings.models import Booking
        
        date_from, date_to = self.get_date_range()
        
        bookings = Booking.objects.all()
        if date_from:
            bookings = bookings.filter(created_at__date__gte=date_from)
        if date_to:
            bookings = bookings.filter(created_at__date__lte=date_to)
        
        # Basic statistics
        total_bookings = bookings.count()
        completed_bookings = bookings.filter(status='completed').count()
        cancelled_bookings = bookings.filter(status='cancelled').count()
        
        # Revenue statistics
        revenue_data = bookings.filter(
            status__in=['confirmed', 'active', 'completed']
        ).aggregate(
            total_revenue=Sum('total_amount'),
            avg_booking_value=Avg('total_amount')
        )
        
        # Booking status distribution
        status_distribution = bookings.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Popular vehicles
        popular_vehicles = bookings.values(
            'vehicle__name', 'vehicle__brand__name'
        ).annotate(
            booking_count=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('-booking_count')[:10]
        
        # Monthly trend
        from django.db.models.functions import TruncMonth
        monthly_trend = bookings.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('month')
        
        return {
            'total_bookings': total_bookings,
            'completed_bookings': completed_bookings,
            'cancelled_bookings': cancelled_bookings,
            'completion_rate': (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0,
            'total_revenue': revenue_data['total_revenue'] or 0,
            'avg_booking_value': revenue_data['avg_booking_value'] or 0,
            'status_distribution': list(status_distribution),
            'popular_vehicles': list(popular_vehicles),
            'monthly_trend': [
                {
                    'month': item['month'].strftime('%Y-%m'),
                    'bookings': item['count'],
                    'revenue': item['revenue'] or 0
                }
                for item in monthly_trend
            ]
        }
    
    def generate_vehicle_utilization(self):
        """Generate vehicle utilization report"""
        from apps.vehicles.models import Vehicle
        from apps.bookings.models import Booking
        
        date_from, date_to = self.get_date_range()
        
        vehicles = Vehicle.objects.filter(is_active=True)
        
        # Calculate utilization for each vehicle
        utilization_data = []
        total_days = (date_to - date_from).days if date_from and date_to else 30
        
        for vehicle in vehicles:
            bookings = Booking.objects.filter(vehicle=vehicle)
            if date_from:
                bookings = bookings.filter(created_at__date__gte=date_from)
            if date_to:
                bookings = bookings.filter(created_at__date__lte=date_to)
            
            booking_count = bookings.count()
            total_booked_days = bookings.aggregate(
                total=Sum('total_days')
            )['total'] or 0
            
            utilization_rate = (total_booked_days / total_days * 100) if total_days > 0 else 0
            
            revenue = bookings.filter(
                status__in=['confirmed', 'active', 'completed']
            ).aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            
            utilization_data.append({
                'vehicle_id': vehicle.id,
                'vehicle_name': f"{vehicle.brand.name} {vehicle.name}",
                'category': vehicle.category.name if vehicle.category else 'Unknown',
                'booking_count': booking_count,
                'total_booked_days': total_booked_days,
                'utilization_rate': round(utilization_rate, 2),
                'revenue': revenue,
                'revenue_per_day': round(revenue / total_booked_days, 2) if total_booked_days > 0 else 0
            })
        
        # Sort by utilization rate
        utilization_data.sort(key=lambda x: x['utilization_rate'], reverse=True)
        
        # Calculate averages
        avg_utilization = sum(item['utilization_rate'] for item in utilization_data) / len(utilization_data) if utilization_data else 0
        total_revenue = sum(item['revenue'] for item in utilization_data)
        
        return {
            'vehicles': utilization_data,
            'avg_utilization_rate': round(avg_utilization, 2),
            'total_revenue': total_revenue,
            'period_days': total_days,
            'top_performers': utilization_data[:5],
            'underperformers': [v for v in utilization_data if v['utilization_rate'] < 20]
        }
    
    def generate_revenue_analysis(self):
        """Generate revenue analysis report"""
        from apps.bookings.models import Booking
        
        date_from, date_to = self.get_date_range()
        
        bookings = Booking.objects.filter(
            status__in=['confirmed', 'active', 'completed']
        )
        if date_from:
            bookings = bookings.filter(created_at__date__gte=date_from)
        if date_to:
            bookings = bookings.filter(created_at__date__lte=date_to)
        
        # Total revenue
        total_revenue = bookings.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Revenue by category
        category_revenue = bookings.values(
            'vehicle__category__name'
        ).annotate(
            revenue=Sum('total_amount'),
            booking_count=Count('id')
        ).order_by('-revenue')
        
        # Revenue by month
        from django.db.models.functions import TruncMonth
        monthly_revenue = bookings.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('total_amount'),
            booking_count=Count('id')
        ).order_by('month')
        
        # Average booking value
        avg_booking_value = bookings.aggregate(
            avg=Avg('total_amount')
        )['avg'] or 0
        
        # Revenue growth
        if len(monthly_revenue) >= 2:
            current_month = monthly_revenue[-1]['revenue'] or 0
            previous_month = monthly_revenue[-2]['revenue'] or 0
            growth_rate = ((current_month - previous_month) / previous_month * 100) if previous_month > 0 else 0
        else:
            growth_rate = 0
        
        return {
            'total_revenue': total_revenue,
            'avg_booking_value': avg_booking_value,
            'growth_rate': round(growth_rate, 2),
            'category_breakdown': list(category_revenue),
            'monthly_trend': [
                {
                    'month': item['month'].strftime('%Y-%m'),
                    'revenue': item['revenue'] or 0,
                    'bookings': item['booking_count']
                }
                for item in monthly_revenue
            ]
        }
    
    def generate_document_compliance(self):
        """Generate document compliance report"""
        try:
            from apps.documents.models import Document, DocumentCategory
            from apps.accounts.models import CustomUser
            
            # Get all users
            users = CustomUser.objects.filter(is_active=True, user_type='customer')
            total_users = users.count()
            
            # Get required document categories
            required_categories = DocumentCategory.objects.filter(
                is_required=True,
                is_active=True
            )
            
            compliance_data = []
            
            for category in required_categories:
                # Users with approved documents in this category
                compliant_users = users.filter(
                    documents__category=category,
                    documents__status='approved'
                ).distinct().count()
                
                compliance_rate = (compliant_users / total_users * 100) if total_users > 0 else 0
                
                compliance_data.append({
                    'category': category.name,
                    'required': True,
                    'compliant_users': compliant_users,
                    'total_users': total_users,
                    'compliance_rate': round(compliance_rate, 2)
                })
            
            # Overall compliance (users with all required documents)
            overall_compliant = 0
            for user in users:
                user_compliant = True
                for category in required_categories:
                    if not user.documents.filter(
                        category=category,
                        status='approved'
                    ).exists():
                        user_compliant = False
                        break
                if user_compliant:
                    overall_compliant += 1
            
            overall_compliance_rate = (overall_compliant / total_users * 100) if total_users > 0 else 0
            
            # Document status breakdown
            all_documents = Document.objects.all()
            status_breakdown = all_documents.values('status').annotate(
                count=Count('id')
            ).order_by('-count')
            
            return {
                'total_users': total_users,
                'overall_compliant_users': overall_compliant,
                'overall_compliance_rate': round(overall_compliance_rate, 2),
                'category_compliance': compliance_data,
                'document_status_breakdown': list(status_breakdown),
                'pending_reviews': all_documents.filter(status='pending').count()
            }
            
        except ImportError:
            return {'error': 'Documents app not available'}
    
    def get_date_range(self):
        """Get date range from filters"""
        date_from = None
        date_to = None
        
        if self.filters.get('date_from'):
            from datetime import datetime
            date_from = datetime.fromisoformat(self.filters['date_from']).date()
        
        if self.filters.get('date_to'):
            from datetime import datetime
            date_to = datetime.fromisoformat(self.filters['date_to']).date()
        
        # Default to last 30 days if no range specified
        if not date_from and not date_to:
            date_to = timezone.now().date()
            date_from = date_to - timedelta(days=30)
        
        return date_from, date_to


class KPICalculator:
    """Calculate KPI values"""
    
    def __init__(self, kpi):
        self.kpi = kpi
        self.config = kpi.calculation_config
    
    def calculate(self):
        """Calculate KPI value based on method"""
        
        method = self.kpi.calculation_method
        
        if method == 'sql':
            return self.calculate_from_sql()
        elif method == 'python':
            return self.calculate_from_python()
        elif method == 'aggregation':
            return self.calculate_from_aggregation()
        else:
            return None
    
    def calculate_from_sql(self):
        """Calculate KPI from SQL query"""
        from django.db import connection
        
        sql_query = self.config.get('sql_query')
        if not sql_query:
            return None
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchone()
                return float(result[0]) if result and result[0] is not None else None
        except Exception:
            return None
    
    def calculate_from_python(self):
        """Calculate KPI from Python function"""
        function_name = self.config.get('function_name')
        if not function_name:
            return None
        
        # This would import and execute a custom function
        # Implementation depends on your specific requirements
        return None
    
    def calculate_from_aggregation(self):
        """Calculate KPI from data aggregation"""
        model_name = self.config.get('model')
        field_name = self.config.get('field')
        aggregation_type = self.config.get('aggregation', 'count')
        filters = self.config.get('filters', {})
        
        if not model_name:
            return None
        
        try:
            # Get model class
            from django.apps import apps
            model_class = apps.get_model(model_name)
            
            # Build queryset
            queryset = model_class.objects.all()
            
            # Apply filters
            for filter_key, filter_value in filters.items():
                queryset = queryset.filter(**{filter_key: filter_value})
            
            # Apply aggregation
            if aggregation_type == 'count':
                return float(queryset.count())
            elif aggregation_type == 'sum' and field_name:
                result = queryset.aggregate(total=Sum(field_name))['total']
                return float(result) if result is not None else 0
            elif aggregation_type == 'avg' and field_name:
                result = queryset.aggregate(avg=Avg(field_name))['avg']
                return float(result) if result is not None else 0
            
        except Exception:
            return None
        
        return None


class ChartDataBuilder:
    """Build chart data for visualization"""
    
    def __init__(self, report):
        self.report = report
        self.data = report.data
    
    def build(self):
        """Build chart data based on report type"""
        
        chart_type = self.report.config.get('chart_type', 'line')
        
        if chart_type == 'line':
            return self.build_line_chart()
        elif chart_type == 'bar':
            return self.build_bar_chart()
        elif chart_type == 'pie':
            return self.build_pie_chart()
        elif chart_type == 'table':
            return self.build_table()
        else:
            return self.build_line_chart()  # Default
    
    def build_line_chart(self):
        """Build line chart data"""
        if 'monthly_trend' in self.data:
            return {
                'type': 'line',
                'labels': [item['month'] for item in self.data['monthly_trend']],
                'datasets': [
                    {
                        'label': 'Bookings',
                        'data': [item['bookings'] for item in self.data['monthly_trend']],
                        'borderColor': 'rgb(75, 192, 192)',
                        'tension': 0.1
                    }
                ]
            }
        
        return {'type': 'line', 'labels': [], 'datasets': []}
    
    def build_bar_chart(self):
        """Build bar chart data"""
        if 'status_distribution' in self.data:
            return {
                'type': 'bar',
                'labels': [item['status'] for item in self.data['status_distribution']],
                'datasets': [
                    {
                        'label': 'Count',
                        'data': [item['count'] for item in self.data['status_distribution']],
                        'backgroundColor': [
                            'rgba(255, 99, 132, 0.2)',
                            'rgba(54, 162, 235, 0.2)',
                            'rgba(255, 205, 86, 0.2)',
                            'rgba(75, 192, 192, 0.2)',
                        ]
                    }
                ]
            }
        
        return {'type': 'bar', 'labels': [], 'datasets': []}
    
    def build_pie_chart(self):
        """Build pie chart data"""
        if 'user_types' in self.data:
            return {
                'type': 'pie',
                'labels': [item['user_type'] for item in self.data['user_types']],
                'datasets': [
                    {
                        'data': [item['count'] for item in self.data['user_types']],
                        'backgroundColor': [
                            '#FF6384',
                            '#36A2EB',
                            '#FFCE56',
                            '#4BC0C0',
                        ]
                    }
                ]
            }
        
        return {'type': 'pie', 'labels': [], 'datasets': []}
    
    def build_table(self):
        """Build table data"""
        # Return raw data for table display
        return {
            'type': 'table',
            'data': self.data
        }


class CustomReportGenerator:
    """Generate custom reports from form data"""
    
    def __init__(self, form_data):
        self.form_data = form_data
    
    def generate(self):
        """Generate custom report"""
        
        data_source = self.form_data['data_source']
        chart_type = self.form_data['chart_type']
        date_range = self.form_data['date_range']
        
        # Get date range
        start_date, end_date = self.get_date_range(date_range)
        
        # Get data based on source
        if data_source == 'bookings':
            data = self.get_booking_data(start_date, end_date)
        elif data_source == 'users':
            data = self.get_user_data(start_date, end_date)
        elif data_source == 'vehicles':
            data = self.get_vehicle_data(start_date, end_date)
        else:
            data = {'error': f'Unknown data source: {data_source}'}
        
        # Format for chart
        chart_data = self.format_for_chart(data, chart_type)
        
        return {
            'chart_data': chart_data,
            'raw_data': data,
            'config': self.form_data
        }
    
    def get_date_range(self, date_range):
        """Get start and end dates from range specification"""
        end_date = timezone.now().date()
        
        if date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif date_range == '90d':
            start_date = end_date - timedelta(days=90)
        elif date_range == '1y':
            start_date = end_date - timedelta(days=365)
        elif date_range == 'custom':
            start_date = self.form_data.get('custom_date_from', end_date - timedelta(days=30))
            end_date = self.form_data.get('custom_date_to', end_date)
        else:
            start_date = end_date - timedelta(days=30)
        
        return start_date, end_date
    
    def get_booking_data(self, start_date, end_date):
        """Get booking data"""
        from apps.bookings.models import Booking
        
        bookings = Booking.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        group_by = self.form_data.get('group_by')
        
        if group_by == 'day':
            from django.db.models.functions import TruncDate
            grouped = bookings.annotate(
                period=TruncDate('created_at')
            ).values('period').annotate(
                count=Count('id')
            ).order_by('period')
        elif group_by == 'week':
            from django.db.models.functions import TruncWeek
            grouped = bookings.annotate(
                period=TruncWeek('created_at')
            ).values('period').annotate(
                count=Count('id')
            ).order_by('period')
        elif group_by == 'month':
            from django.db.models.functions import TruncMonth
            grouped = bookings.annotate(
                period=TruncMonth('created_at')
            ).values('period').annotate(
                count=Count('id')
            ).order_by('period')
        else:
            # No grouping - just total count
            return {'total_bookings': bookings.count()}
        
        return [
            {
                'period': item['period'].isoformat(),
                'count': item['count']
            }
            for item in grouped
        ]
    
    def get_user_data(self, start_date, end_date):
        """Get user data"""
        from apps.accounts.models import CustomUser
        
        users = CustomUser.objects.filter(
            date_joined__date__range=[start_date, end_date]
        )
        
        return {
            'total_users': users.count(),
            'by_type': list(users.values('user_type').annotate(
                count=Count('id')
            ).order_by('-count'))
        }
    
    def get_vehicle_data(self, start_date, end_date):
        """Get vehicle data"""
        from apps.vehicles.models import Vehicle
        
        vehicles = Vehicle.objects.filter(is_active=True)
        
        return {
            'total_vehicles': vehicles.count(),
            'by_category': list(vehicles.values('category__name').annotate(
                count=Count('id')
            ).order_by('-count'))
        }
    
    def format_for_chart(self, data, chart_type):
        """Format data for specific chart type"""
        
        if chart_type == 'line' and isinstance(data, list):
            return {
                'type': 'line',
                'labels': [item['period'] for item in data],
                'datasets': [
                    {
                        'label': 'Count',
                        'data': [item['count'] for item in data],
                        'borderColor': 'rgb(75, 192, 192)',
                        'tension': 0.1
                    }
                ]
            }
        elif chart_type == 'bar' and 'by_type' in data:
            return {
                'type': 'bar',
                'labels': [item['user_type'] for item in data['by_type']],
                'datasets': [
                    {
                        'label': 'Count',
                        'data': [item['count'] for item in data['by_type']],
                        'backgroundColor': 'rgba(54, 162, 235, 0.2)'
                    }
                ]
            }
        
        # Default table format
        return {
            'type': 'table',
            'data': data
        }
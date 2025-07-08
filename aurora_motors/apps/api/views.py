from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import timedelta

# Import serializers from each app
from apps.accounts.serializers import UserSerializer, UserProfileSerializer
from apps.vehicles.serializers import VehicleListSerializer, VehicleDetailSerializer
from apps.bookings.serializers import BookingSerializer
from apps.documents.serializers import DocumentListSerializer, DocumentDetailSerializer
from apps.contracts.serializers import ContractListSerializer, ContractDetailSerializer
from apps.notifications.serializers import NotificationSerializer

# Import models
from apps.accounts.models import CustomUser
from apps.vehicles.models import Vehicle
from apps.bookings.models import Booking
from apps.documents.models import Document
from apps.contracts.models import Contract
from apps.notifications.models import Notification

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class APIRootView(APIView):
    """API root endpoint with available endpoints"""
    
    def get(self, request, format=None):
        return Response({
            'message': 'Welcome to Aurora Motors API',
            'version': '1.0',
            'endpoints': {
                'authentication': '/api/auth/',
                'users': '/api/v1/users/',
                'vehicles': '/api/v1/vehicles/',
                'bookings': '/api/v1/bookings/',
                'documents': '/api/v1/documents/',
                'contracts': '/api/v1/contracts/',
                'notifications': '/api/v1/notifications/',
                'dashboard': '/api/v1/dashboard/',
                'documentation': '/api/docs/',
            }
        })

class RefreshTokenView(APIView):
    """Refresh authentication token"""
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                token, created = Token.objects.get_or_create(user=user)
                return Response({'token': token.key})
        
        return Response(
            {'error': 'Invalid credentials'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

class UserViewSet(viewsets.ModelViewSet):
    """User management API"""
    
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        # Staff can see all users, others only themselves
        if self.request.user.is_staff:
            return CustomUser.objects.all()
        return CustomUser.objects.filter(id=self.request.user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        """Update current user profile"""
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VehicleViewSet(viewsets.ReadOnlyModelViewSet):
    """Vehicle API"""
    
    queryset = Vehicle.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VehicleDetailSerializer
        return VehicleListSerializer
    
    def get_queryset(self):
        queryset = Vehicle.objects.filter(is_active=True)
        
        # Filter by availability
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date and end_date:
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_date).date()
                end_dt = datetime.fromisoformat(end_date).date()
                queryset = queryset.available_for_period(start_dt, end_dt)
            except ValueError:
                pass
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__name__icontains=category)
        
        # Filter by brand
        brand = self.request.query_params.get('brand')
        if brand:
            queryset = queryset.filter(brand__name__icontains=brand)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(daily_rate__gte=min_price)
        if max_price:
            queryset = queryset.filter(daily_rate__lte=max_price)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Check vehicle availability"""
        vehicle = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_date).date()
            end_dt = datetime.fromisoformat(end_date).date()
            
            is_available = vehicle.is_available_for_period(start_dt, end_dt)
            duration = (end_dt - start_dt).days
            
            return Response({
                'available': is_available,
                'duration_days': duration,
                'daily_rate': vehicle.daily_rate,
                'total_cost': vehicle.get_rate_for_duration(duration) if is_available else None
            })
        
        except ValueError:
            return Response(
                {'error': 'Invalid date format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class BookingViewSet(viewsets.ModelViewSet):
    """Booking management API"""
    
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        # Users can only see their own bookings (except staff)
        if self.request.user.is_staff:
            return Booking.objects.all()
        return Booking.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        
        if not booking.can_be_cancelled:
            return Response(
                {'error': 'This booking cannot be cancelled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'customer_request')
        notes = request.data.get('notes', '')
        
        booking.cancel_booking(request.user, reason, notes)
        
        return Response({'message': 'Booking cancelled successfully'})
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming bookings for user"""
        upcoming_bookings = self.get_queryset().filter(
            status__in=['confirmed', 'active'],
            start_date__gte=timezone.now()
        ).order_by('start_date')
        
        serializer = self.get_serializer(upcoming_bookings, many=True)
        return Response(serializer.data)

class DocumentViewSet(viewsets.ModelViewSet):
    """Document management API"""
    
    queryset = Document.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        # Users can only see their own documents (except staff)
        if self.request.user.is_staff:
            return Document.objects.all()
        return Document.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DocumentDetailSerializer
        return DocumentListSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending documents"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_docs = Document.objects.filter(status='pending')
        serializer = self.get_serializer(pending_docs, many=True)
        return Response(serializer.data)

class ContractViewSet(viewsets.ReadOnlyModelViewSet):
    """Contract management API"""
    
    queryset = Contract.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        # Users can only see their own contracts (except staff)
        if self.request.user.is_staff:
            return Contract.objects.all()
        return Contract.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ContractDetailSerializer
        return ContractListSerializer

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Notification management API"""
    
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.mark_read()
        return Response({'message': 'Notification marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        updated = self.get_queryset().exclude(status='read').update(
            status='read',
            read_at=timezone.now()
        )
        return Response({'message': f'{updated} notifications marked as read'})

class DashboardAPIView(APIView):
    """Dashboard data API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.is_staff:
            # Staff dashboard
            data = {
                'total_users': CustomUser.objects.filter(is_active=True).count(),
                'total_vehicles': Vehicle.objects.filter(is_active=True).count(),
                'total_bookings': Booking.objects.count(),
                'active_bookings': Booking.objects.filter(status='active').count(),
                'pending_documents': Document.objects.filter(status='pending').count(),
                'recent_bookings': BookingSerializer(
                    Booking.objects.order_by('-created_at')[:5], many=True
                ).data
            }
        else:
            # Customer dashboard
            user_bookings = Booking.objects.filter(user=user)
            data = {
                'total_bookings': user_bookings.count(),
                'upcoming_bookings': user_bookings.filter(
                    status__in=['confirmed', 'active'],
                    start_date__gte=timezone.now()
                ).count(),
                'pending_documents': Document.objects.filter(
                    user=user, status='pending'
                ).count(),
                'unread_notifications': Notification.objects.filter(
                    recipient=user
                ).exclude(status='read').count(),
                'recent_bookings': BookingSerializer(
                    user_bookings.order_by('-created_at')[:3], many=True
                ).data
            }
        
        return Response(data)

class VehicleAvailabilityAPIView(APIView):
    """Vehicle availability checking API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_date).date()
            end_dt = datetime.fromisoformat(end_date).date()
            
            available_vehicles = Vehicle.objects.available_for_period(start_dt, end_dt)
            serializer = VehicleListSerializer(available_vehicles, many=True)
            
            return Response({
                'available_vehicles': serializer.data,
                'total_available': available_vehicles.count(),
                'search_dates': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'duration_days': (end_dt - start_dt).days
                }
            })
        
        except ValueError:
            return Response(
                {'error': 'Invalid date format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class BookingCalendarAPIView(APIView):
    """Booking calendar data API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        start_date = request.query_params.get('start')
        end_date = request.query_params.get('end')
        vehicle_id = request.query_params.get('vehicle_id')
        
        bookings = Booking.objects.filter(status__in=['confirmed', 'active'])
        
        if start_date and end_date:
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_date)
                end_dt = datetime.fromisoformat(end_date)
                bookings = bookings.filter(
                    start_date__lte=end_dt,
                    end_date__gte=start_dt
                )
            except ValueError:
                pass
        
        if vehicle_id:
            bookings = bookings.filter(vehicle_id=vehicle_id)
        
        # Format for calendar
        events = []
        for booking in bookings:
            events.append({
                'id': booking.id,
                'title': f"{booking.booking_number} - {booking.user.get_full_name()}",
                'start': booking.start_date.isoformat(),
                'end': booking.end_date.isoformat(),
                'color': self.get_booking_color(booking.status),
                'extendedProps': {
                    'booking_number': booking.booking_number,
                    'customer': booking.user.get_full_name(),
                    'vehicle': str(booking.vehicle),
                    'status': booking.status,
                }
            })
        
        return Response(events)
    
    def get_booking_color(self, status):
        colors = {
            'confirmed': '#007bff',
            'active': '#28a745',
            'pending': '#ffc107',
            'completed': '#6c757d',
            'cancelled': '#dc3545',
        }
        return colors.get(status, '#6c757d')

class AnalyticsAPIView(APIView):
    """Analytics data API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Booking analytics
        bookings = Booking.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        # Revenue analytics
        revenue_data = bookings.filter(
            status__in=['confirmed', 'active', 'completed']
        ).aggregate(
            total_revenue=Sum('total_amount'),
            avg_booking_value=Sum('total_amount')
        )
        
        data = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'bookings': {
                'total': bookings.count(),
                'by_status': dict(bookings.values_list('status').annotate(Count('status'))),
            },
            'revenue': {
                'total': float(revenue_data['total_revenue'] or 0),
                'average_booking': float(revenue_data['avg_booking_value'] or 0),
            },
            'vehicles': {
                'total_active': Vehicle.objects.filter(is_active=True).count(),
                'most_booked': self.get_most_booked_vehicles(start_date, end_date),
            }
        }
        
        return Response(data)
    
    def get_most_booked_vehicles(self, start_date, end_date):
        return list(Vehicle.objects.annotate(
            booking_count=Count(
                'bookings',
                filter=Q(bookings__created_at__date__range=[start_date, end_date])
            )
        ).filter(booking_count__gt=0).order_by('-booking_count')[:5].values(
            'id', 'name', 'brand__name', 'booking_count'
        ))

class UserProfileAPIView(APIView):
    """User profile API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user.profile)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserProfileSerializer(
            request.user.profile, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserBookingsAPIView(APIView):
    """User bookings API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

class UserDocumentsAPIView(APIView):
    """User documents API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        documents = Document.objects.filter(user=request.user).order_by('-created_at')
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)

class UserNotificationsAPIView(APIView):
    """User notifications API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        notifications = Notification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class APIDocumentationView(APIView):
    """API documentation endpoint"""
    
    def get(self, request):
        return Response({
            'title': 'Aurora Motors API Documentation',
            'version': '1.0',
            'description': 'REST API for Aurora Motors car rental system',
            'authentication': 'Token-based authentication required',
            'endpoints': {
                'Authentication': {
                    'POST /api/auth/token/': 'Obtain authentication token',
                    'POST /api/auth/refresh/': 'Refresh authentication token',
                },
                'Users': {
                    'GET /api/v1/users/': 'List users',
                    'GET /api/v1/users/me/': 'Get current user profile',
                    'PUT /api/v1/users/update_profile/': 'Update current user profile',
                },
                'Vehicles': {
                    'GET /api/v1/vehicles/': 'List available vehicles',
                    'GET /api/v1/vehicles/{id}/': 'Get vehicle details',
                    'GET /api/v1/vehicles/{id}/availability/': 'Check vehicle availability',
                },
                'Bookings': {
                    'GET /api/v1/bookings/': 'List user bookings',
                    'POST /api/v1/bookings/': 'Create new booking',
                    'GET /api/v1/bookings/{id}/': 'Get booking details',
                    'POST /api/v1/bookings/{id}/cancel/': 'Cancel booking',
                    'GET /api/v1/bookings/upcoming/': 'Get upcoming bookings',
                },
                'Documents': {
                    'GET /api/v1/documents/': 'List user documents',
                    'POST /api/v1/documents/': 'Upload new document',
                    'GET /api/v1/documents/pending/': 'Get pending documents (staff only)',
                },
                'Contracts': {
                    'GET /api/v1/contracts/': 'List user contracts',
                    'GET /api/v1/contracts/{id}/': 'Get contract details',
                },
                'Notifications': {
                    'GET /api/v1/notifications/': 'List user notifications',
                    'POST /api/v1/notifications/{id}/mark_read/': 'Mark notification as read',
                    'POST /api/v1/notifications/mark_all_read/': 'Mark all notifications as read',
                },
                'Dashboard': {
                    'GET /api/v1/dashboard/': 'Get dashboard data',
                },
                'Utility': {
                    'GET /api/v1/vehicle-availability/': 'Check vehicle availability for date range',
                    'GET /api/v1/booking-calendar/': 'Get booking calendar data',
                    'GET /api/v1/analytics/': 'Get analytics data (staff only)',
                }
            },
            'query_parameters': {
                'pagination': 'page, page_size',
                'vehicles': 'start_date, end_date, category, brand, min_price, max_price',
                'calendar': 'start, end, vehicle_id',
                'analytics': 'days (default: 30)',
            }
        })
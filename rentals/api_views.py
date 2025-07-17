from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from datetime import datetime
import json

from .models import Vehicle, Booking, VehicleCategory, Location, UserProfile
from .serializers import VehicleSerializer, BookingSerializer, VehicleCategorySerializer, LocationSerializer
from .utils import check_vehicle_availability, calculate_rental_days, calculate_total_amount

class VehicleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Vehicle.objects.filter(status='available')
    serializer_class = VehicleSerializer

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

class VehicleCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VehicleCategory.objects.all()
    serializer_class = VehicleCategorySerializer

class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.filter(is_active=True)
    serializer_class = LocationSerializer

@api_view(['GET'])
def search_availability(request):
    """Search for available vehicles"""
    pickup_date = request.GET.get('pickup_date')
    dropoff_date = request.GET.get('dropoff_date')
    vehicle_type = request.GET.get('vehicle_type')
    
    if not pickup_date or not dropoff_date:
        return Response({
            'success': False,
            'error': 'Pickup and dropoff dates are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Convert strings to datetime
        pickup = datetime.fromisoformat(pickup_date.replace('Z', '+00:00'))
        dropoff = datetime.fromisoformat(dropoff_date.replace('Z', '+00:00'))
        
        # Find available vehicles
        booked_vehicles = Booking.objects.filter(
            start_date__lt=dropoff,
            end_date__gt=pickup,
            status__in=['confirmed', 'active']
        ).values_list('vehicle_id', flat=True)
        
        available_vehicles = Vehicle.objects.filter(
            status='available'
        ).exclude(id__in=booked_vehicles)
        
        if vehicle_type:
            available_vehicles = available_vehicles.filter(category_id=vehicle_type)
        
        # Calculate pricing for the period
        total_days = calculate_rental_days(pickup, dropoff)
        vehicle_data = []
        
        for vehicle in available_vehicles:
            vehicle_data.append({
                'id': str(vehicle.id),
                'name': vehicle.display_name,
                'category': vehicle.category.name,
                'daily_rate': float(vehicle.price_per_day),
                'total_price': float(vehicle.price_per_day * total_days),
                'image': vehicle.images.first().image.url if vehicle.images.exists() else None,
                'seats': vehicle.seats,
                'transmission': vehicle.get_transmission_display(),
                'fuel_type': vehicle.get_fuel_type_display(),
            })
        
        return Response({
            'success': True,
            'vehicles': vehicle_data,
            'total_days': total_days,
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'error': 'Invalid date format'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_pricing(request):
    """Calculate pricing for a vehicle rental"""
    vehicle_id = request.GET.get('vehicle_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not all([vehicle_id, start_date, end_date]):
        return Response({
            'success': False,
            'error': 'Missing required parameters'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        total_days = calculate_rental_days(start, end)
        total_amount = calculate_total_amount(vehicle.price_per_day, total_days)
        
        return Response({
            'success': True,
            'daily_rate': float(vehicle.price_per_day),
            'total_days': total_days,
            'subtotal': float(total_amount),
            'security_deposit': float(vehicle.security_deposit),
            'total_amount': float(total_amount + vehicle.security_deposit),
        })
        
    except Vehicle.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Vehicle not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except ValueError:
        return Response({
            'success': False,
            'error': 'Invalid date format'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, booking_id):
    """Cancel a booking"""
    try:
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        
        if booking.status not in ['pending', 'confirmed']:
            return Response({
                'success': False,
                'error': 'Booking cannot be cancelled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        booking.status = 'cancelled'
        booking.save()
        
        return Response({
            'success': True,
            'message': 'Booking cancelled successfully'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sign_contract(request):
    """Handle contract signing"""
    try:
        data = json.loads(request.body)
        signature = data.get('signature')
        agree_terms = data.get('agree_terms')
        
        if not signature or not agree_terms:
            return Response({
                'success': False,
                'error': 'Signature and agreement are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.contract_signed = True
        profile.contract_signature = signature
        profile.save()
        
        return Response({
            'success': True,
            'message': 'Contract signed successfully',
            'redirect_url': '/dashboard/'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
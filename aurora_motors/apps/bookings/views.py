from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
import json
from datetime import datetime, timedelta

from .models import Booking, BookingExtension, BookingAdditionalDriver, BookingNote, BookingInvoice
from .forms import (
    BookingForm, BookingUpdateForm, BookingCancellationForm, BookingExtensionForm,
    AdditionalDriverForm, BookingNoteForm, BookingSearchForm, VehiclePickupForm,
    VehicleReturnForm
)
from apps.vehicles.models import Vehicle
from apps.accounts.permissions import (
    CustomerRequiredMixin, StaffRequiredMixin, VerifiedUserRequiredMixin,
    ProfileCompleteRequiredMixin
)
from apps.notifications.tasks import send_booking_confirmation, send_booking_reminder


class BookingCreateView(LoginRequiredMixin, VerifiedUserRequiredMixin, ProfileCompleteRequiredMixin, CreateView):
    """Create a new booking"""
    
    model = Booking
    form_class = BookingForm
    template_name = 'bookings/booking_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.vehicle = get_object_or_404(Vehicle, pk=kwargs['vehicle_pk'], is_active=True)
        
        # Check if user can book
        can_book, message = request.user.can_book_vehicle()
        if not can_book:
            messages.error(request, f"Cannot create booking: {message}")
            return redirect('vehicles:detail', pk=self.vehicle.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['vehicle'] = self.vehicle
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Send confirmation email
        send_booking_confirmation.delay(self.object.id)
        
        messages.success(
            self.request,
            f'Booking {self.object.booking_number} created successfully! '
            f'You will receive a confirmation email shortly.'
        )
        
        return response
    
    def get_success_url(self):
        return reverse('bookings:detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vehicle'] = self.vehicle
        
        # Calculate estimated pricing
        if self.request.GET.get('start_date') and self.request.GET.get('end_date'):
            try:
                start_date = datetime.fromisoformat(self.request.GET['start_date'].replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(self.request.GET['end_date'].replace('Z', '+00:00'))
                days = (end_date.date() - start_date.date()).days
                if days == 0:
                    days = 1
                
                context['estimated_days'] = days
                context['estimated_cost'] = self.vehicle.get_rate_for_duration(days)
                context['security_deposit'] = self.vehicle.security_deposit
            except (ValueError, TypeError):
                pass
        
        return context


class BookingDetailView(LoginRequiredMixin, DetailView):
    """Booking detail view"""
    
    model = Booking
    template_name = 'bookings/booking_detail.html'
    context_object_name = 'booking'
    
    def get_queryset(self):
        queryset = Booking.objects.select_related(
            'user', 'vehicle', 'vehicle__brand', 'cancelled_by'
        ).prefetch_related(
            'additional_drivers', 'extensions', 'notes', 'invoices'
        )
        
        # Staff can see all bookings, customers only their own
        if self.request.user.is_staff_member or self.request.user.is_admin_user:
            return queryset
        else:
            return queryset.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.object
        
        # Add forms for various actions
        context['cancellation_form'] = BookingCancellationForm()
        context['extension_form'] = BookingExtensionForm(booking=booking)
        context['note_form'] = BookingNoteForm()
        context['additional_driver_form'] = AdditionalDriverForm(booking=booking)
        
        # Add pickup/return forms for staff
        if self.request.user.is_staff_member or self.request.user.is_admin_user:
            context['pickup_form'] = VehiclePickupForm()
            context['return_form'] = VehicleReturnForm()
        
        # Check if booking can be modified
        context['can_cancel'] = booking.can_be_cancelled
        context['can_extend'] = booking.status in ['confirmed', 'active']
        context['can_pickup'] = booking.status == 'confirmed'
        context['can_return'] = booking.status == 'active'
        
        return context


class BookingListView(LoginRequiredMixin, ListView):
    """Booking list view"""
    
    model = Booking
    template_name = 'bookings/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Booking.objects.select_related(
            'user', 'vehicle', 'vehicle__brand'
        ).order_by('-created_at')
        
        # Staff can see all bookings, customers only their own
        if not (self.request.user.is_staff_member or self.request.user.is_admin_user):
            queryset = queryset.filter(user=self.request.user)
        
        # Apply search filters
        self.search_form = BookingSearchForm(self.request.GET)
        if self.search_form.is_valid():
            search = self.search_form.cleaned_data.get('search')
            status = self.search_form.cleaned_data.get('status')
            start_date = self.search_form.cleaned_data.get('start_date')
            end_date = self.search_form.cleaned_data.get('end_date')
            vehicle = self.search_form.cleaned_data.get('vehicle')
            
            if search:
                queryset = queryset.filter(
                    Q(booking_number__icontains=search) |
                    Q(user__first_name__icontains=search) |
                    Q(user__last_name__icontains=search) |
                    Q(user__email__icontains=search) |
                    Q(vehicle__name__icontains=search) |
                    Q(vehicle__registration_number__icontains=search)
                )
            
            if status:
                queryset = queryset.filter(status=status)
            
            if start_date:
                queryset = queryset.filter(start_date__date__gte=start_date)
            
            if end_date:
                queryset = queryset.filter(end_date__date__lte=end_date)
            
            if vehicle:
                queryset = queryset.filter(vehicle=vehicle)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = getattr(self, 'search_form', BookingSearchForm())
        
        # Add statistics for staff
        if self.request.user.is_staff_member or self.request.user.is_admin_user:
            context['stats'] = Booking.objects.for_dashboard()
        
        return context


class BookingUpdateView(StaffRequiredMixin, UpdateView):
    """Update booking (staff only)"""
    
    model = Booking
    form_class = BookingUpdateForm
    template_name = 'bookings/booking_update.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Booking updated successfully!')
        return super().form_valid(form)


@login_required
def cancel_booking(request, pk):
    """Cancel a booking"""
    
    booking = get_object_or_404(Booking, pk=pk)
    
    # Check permissions
    if not (booking.user == request.user or request.user.is_staff_member or request.user.is_admin_user):
        messages.error(request, 'You do not have permission to cancel this booking.')
        return redirect('bookings:detail', pk=booking.pk)
    
    # Check if booking can be cancelled
    if not booking.can_be_cancelled:
        messages.error(request, 'This booking cannot be cancelled.')
        return redirect('bookings:detail', pk=booking.pk)
    
    if request.method == 'POST':
        form = BookingCancellationForm(request.POST)
        if form.is_valid():
            booking.cancel_booking(
                cancelled_by=request.user,
                reason=form.cleaned_data['reason'],
                notes=form.cleaned_data['notes']
            )
            
            messages.success(request, f'Booking {booking.booking_number} has been cancelled.')
            return redirect('bookings:detail', pk=booking.pk)
    else:
        form = BookingCancellationForm()
    
    return render(request, 'bookings/booking_cancel.html', {
        'booking': booking,
        'form': form
    })


@login_required
def extend_booking(request, pk):
    """Request booking extension"""
    
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    # Check if booking can be extended
    if booking.status not in ['confirmed', 'active']:
        messages.error(request, 'This booking cannot be extended.')
        return redirect('bookings:detail', pk=booking.pk)
    
    if request.method == 'POST':
        form = BookingExtensionForm(request.POST, booking=booking)
        if form.is_valid():
            extension = form.save()
            
            messages.success(
                request,
                'Extension request submitted successfully. You will be notified once it is reviewed.'
            )
            return redirect('bookings:detail', pk=booking.pk)
    else:
        form = BookingExtensionForm(booking=booking)
    
    return render(request, 'bookings/booking_extend.html', {
        'booking': booking,
        'form': form
    })


@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def process_extension(request, pk, extension_pk):
    """Process booking extension request (staff only)"""
    
    booking = get_object_or_404(Booking, pk=pk)
    extension = get_object_or_404(BookingExtension, pk=extension_pk, booking=booking)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            extension.approve(request.user, notes)
            messages.success(request, 'Extension approved successfully.')
        elif action == 'reject':
            extension.reject(request.user, notes)
            messages.success(request, 'Extension rejected.')
        
        return redirect('bookings:detail', pk=booking.pk)
    
    return render(request, 'bookings/extension_process.html', {
        'booking': booking,
        'extension': extension
    })


@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def vehicle_pickup(request, pk):
    """Process vehicle pickup (staff only)"""
    
    booking = get_object_or_404(Booking, pk=pk)
    
    if booking.status != 'confirmed':
        messages.error(request, 'Vehicle can only be picked up for confirmed bookings.')
        return redirect('bookings:detail', pk=booking.pk)
    
    if request.method == 'POST':
        form = VehiclePickupForm(request.POST)
        if form.is_valid():
            pickup_mileage = form.cleaned_data['pickup_mileage']
            condition_notes = form.cleaned_data['vehicle_condition_notes']
            
            # Start the rental
            booking.start_rental(pickup_mileage)
            
            # Add pickup note
            if condition_notes:
                BookingNote.objects.create(
                    booking=booking,
                    author=request.user,
                    content=f"Vehicle pickup - Mileage: {pickup_mileage}km. Condition: {condition_notes}",
                    is_important=True
                )
            
            messages.success(request, f'Vehicle pickup processed for booking {booking.booking_number}.')
            return redirect('bookings:detail', pk=booking.pk)
    else:
        form = VehiclePickupForm()
        # Pre-fill with current vehicle mileage
        form.fields['pickup_mileage'].initial = booking.vehicle.mileage
    
    return render(request, 'bookings/vehicle_pickup.html', {
        'booking': booking,
        'form': form
    })


@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def vehicle_return(request, pk):
    """Process vehicle return (staff only)"""
    
    booking = get_object_or_404(Booking, pk=pk)
    
    if booking.status != 'active':
        messages.error(request, 'Vehicle can only be returned for active bookings.')
        return redirect('bookings:detail', pk=booking.pk)
    
    if request.method == 'POST':
        form = VehicleReturnForm(request.POST)
        if form.is_valid():
            return_mileage = form.cleaned_data['return_mileage']
            fuel_level = form.cleaned_data['fuel_level']
            vehicle_condition = form.cleaned_data['vehicle_condition']
            damage_notes = form.cleaned_data['damage_notes']
            additional_charges = form.cleaned_data['additional_charges'] or 0
            
            # Complete the rental
            booking.complete_rental(return_mileage)
            
            # Calculate excess mileage if any
            excess_fee = booking.excess_mileage_fee
            total_additional = additional_charges + excess_fee
            
            if total_additional > 0:
                booking.additional_fees += total_additional
                booking.total_amount += total_additional
                booking.save()
            
            # Add return note
            return_note = f"Vehicle return - Mileage: {return_mileage}km, Fuel: {fuel_level}, Condition: {vehicle_condition}"
            if damage_notes:
                return_note += f", Damage: {damage_notes}"
            if excess_fee > 0:
                return_note += f", Excess mileage fee: ${excess_fee}"
            if additional_charges > 0:
                return_note += f", Additional charges: ${additional_charges}"
            
            BookingNote.objects.create(
                booking=booking,
                author=request.user,
                content=return_note,
                is_important=True
            )
            
            messages.success(request, f'Vehicle return processed for booking {booking.booking_number}.')
            return redirect('bookings:detail', pk=booking.pk)
    else:
        form = VehicleReturnForm()
    
    return render(request, 'bookings/vehicle_return.html', {
        'booking': booking,
        'form': form
    })


@login_required
def add_booking_note(request, pk):
    """Add a note to booking"""
    
    booking = get_object_or_404(Booking, pk=pk)
    
    # Check permissions
    if not (booking.user == request.user or request.user.is_staff_member or request.user.is_admin_user):
        messages.error(request, 'You do not have permission to add notes to this booking.')
        return redirect('bookings:detail', pk=booking.pk)
    
    if request.method == 'POST':
        form = BookingNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.booking = booking
            note.author = request.user
            note.save()
            
            messages.success(request, 'Note added successfully.')
            return redirect('bookings:detail', pk=booking.pk)
    
    return redirect('bookings:detail', pk=booking.pk)


@login_required
def add_additional_driver(request, pk):
    """Add additional driver to booking"""
    
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    if booking.status not in ['pending', 'confirmed']:
        messages.error(request, 'Additional drivers can only be added to pending or confirmed bookings.')
        return redirect('bookings:detail', pk=booking.pk)
    
    if request.method == 'POST':
        form = AdditionalDriverForm(request.POST, booking=booking)
        if form.is_valid():
            additional_driver = form.save(commit=False)
            additional_driver.booking = booking
            additional_driver.save()
            
            messages.success(request, 'Additional driver added successfully.')
            return redirect('bookings:detail', pk=booking.pk)
    
    return redirect('bookings:detail', pk=booking.pk)


class BookingCalendarView(StaffRequiredMixin, TemplateView):
    """Booking calendar view for staff"""
    
    template_name = 'bookings/booking_calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all vehicles for filter
        context['vehicles'] = Vehicle.objects.filter(is_active=True)
        
        return context


# AJAX Views
@require_http_methods(["GET"])
@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def booking_calendar_data(request):
    """Get booking data for calendar"""
    
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    vehicle_id = request.GET.get('vehicle')
    
    bookings = Booking.objects.filter(
        status__in=['confirmed', 'active']
    ).select_related('user', 'vehicle')
    
    if start_date and end_date:
        bookings = bookings.filter(
            start_date__date__lte=end_date,
            end_date__date__gte=start_date
        )
    
    if vehicle_id:
        bookings = bookings.filter(vehicle_id=vehicle_id)
    
    events = []
    for booking in bookings:
        color = {
            'confirmed': '#007bff',
            'active': '#28a745',
            'pending': '#ffc107',
        }.get(booking.status, '#6c757d')
        
        events.append({
            'id': booking.id,
            'title': f"{booking.booking_number} - {booking.user.get_full_name()}",
            'start': booking.start_date.isoformat(),
            'end': booking.end_date.isoformat(),
            'color': color,
            'url': reverse('bookings:detail', kwargs={'pk': booking.pk}),
            'extendedProps': {
                'booking_number': booking.booking_number,
                'customer': booking.user.get_full_name(),
                'vehicle': str(booking.vehicle),
                'status': booking.get_status_display(),
            }
        })
    
    return JsonResponse(events, safe=False)


@require_http_methods(["GET"])
@login_required
def booking_statistics(request):
    """Get booking statistics"""
    
    if not (request.user.is_staff_member or request.user.is_admin_user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    bookings = Booking.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    stats = {
        'total_bookings': bookings.count(),
        'revenue': float(bookings.aggregate(
            total=Sum('total_amount')
        )['total'] or 0),
        'average_booking_value': float(bookings.aggregate(
            avg=Avg('total_amount')
        )['avg'] or 0),
        'by_status': {},
        'daily_bookings': [],
        'popular_vehicles': [],
    }
    
    # Bookings by status
    status_counts = bookings.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    for item in status_counts:
        stats['by_status'][item['status']] = item['count']
    
    # Daily booking counts
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    
    daily_data = bookings.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    for item in daily_data:
        stats['daily_bookings'].append({
            'date': item['date'].isoformat(),
            'count': item['count']
        })
    
    # Popular vehicles
    vehicle_data = bookings.values(
        'vehicle__name', 'vehicle__brand__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    for item in vehicle_data:
        stats['popular_vehicles'].append({
            'vehicle': f"{item['vehicle__brand__name']} {item['vehicle__name']}",
            'bookings': item['count']
        })
    
    return JsonResponse(stats)


@require_http_methods(["POST"])
@login_required
def quick_booking_check(request):
    """Quick availability check"""
    
    data = json.loads(request.body)
    vehicle_id = data.get('vehicle_id')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id, is_active=True)
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        is_available = vehicle.is_available_for_period(start_dt.date(), end_dt.date())
        
        if is_available:
            duration = (end_dt.date() - start_dt.date()).days
            if duration == 0:
                duration = 1
            
            total_cost = vehicle.get_rate_for_duration(duration)
            
            return JsonResponse({
                'available': True,
                'duration': duration,
                'daily_rate': float(vehicle.daily_rate),
                'total_cost': float(total_cost),
                'security_deposit': float(vehicle.security_deposit)
            })
        else:
            return JsonResponse({
                'available': False,
                'message': 'Vehicle not available for selected dates'
            })
    
    except (Vehicle.DoesNotExist, ValueError) as e:
        return JsonResponse({
            'available': False,
            'message': 'Invalid request'
        }, status=400)


# Dashboard Views
class BookingDashboardView(StaffRequiredMixin, TemplateView):
    """Booking management dashboard"""
    
    template_name = 'bookings/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        today = timezone.now().date()
        
        # Today's statistics
        context['todays_pickups'] = Booking.objects.filter(
            status='confirmed',
            start_date__date=today
        ).count()
        
        context['todays_returns'] = Booking.objects.filter(
            status='active',
            end_date__date=today
        ).count()
        
        context['active_rentals'] = Booking.objects.filter(
            status='active'
        ).count()
        
        context['overdue_returns'] = Booking.objects.overdue().count()
        
        # Recent bookings
        context['recent_bookings'] = Booking.objects.select_related(
            'user', 'vehicle'
        ).order_by('-created_at')[:10]
        
        # Pending extensions
        context['pending_extensions'] = BookingExtension.objects.filter(
            status='pending'
        ).select_related('booking', 'booking__user')[:5]
        
        # Revenue statistics
        this_month = Booking.objects.filter(
            created_at__year=today.year,
            created_at__month=today.month,
            status__in=['confirmed', 'active', 'completed']
        )
        
        context['monthly_revenue'] = this_month.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        context['monthly_bookings'] = this_month.count()
        
        return context


def booking_invoice_pdf(request, pk):
    """Generate booking invoice PDF"""
    
    booking = get_object_or_404(Booking, pk=pk)
    
    # Check permissions
    if not (booking.user == request.user or request.user.is_staff_member or request.user.is_admin_user):
        messages.error(request, 'You do not have permission to view this invoice.')
        return redirect('bookings:detail', pk=booking.pk)
    
    # Generate PDF using reportlab
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Header
    story.append(Paragraph("AURORA MOTORS PTY LTD", styles['Title']))
    story.append(Paragraph("Car Rental Invoice", styles['Heading1']))
    story.append(Spacer(1, 20))
    
    # Invoice details
    invoice_data = [
        ['Invoice Number:', booking.booking_number],
        ['Invoice Date:', timezone.now().strftime('%Y-%m-%d')],
        ['Customer:', booking.user.get_full_name()],
        ['Email:', booking.user.email],
        ['Vehicle:', str(booking.vehicle)],
        ['Rental Period:', f"{booking.start_date.strftime('%Y-%m-%d %H:%M')} to {booking.end_date.strftime('%Y-%m-%d %H:%M')}"],
    ]
    
    invoice_table = Table(invoice_data)
    invoice_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(invoice_table)
    story.append(Spacer(1, 30))
    
    # Billing details
    billing_data = [
        ['Description', 'Days', 'Rate', 'Amount'],
        ['Vehicle Rental', str(booking.total_days), f"${booking.daily_rate}", f"${booking.subtotal}"],
    ]
    
    if booking.insurance_amount > 0:
        billing_data.append(['Insurance', '', '', f"${booking.insurance_amount}"])
    
    if booking.additional_fees > 0:
        billing_data.append(['Additional Fees', '', '', f"${booking.additional_fees}"])
    
    if booking.discount_amount > 0:
        billing_data.append(['Discount', '', '', f"-${booking.discount_amount}"])
    
    billing_data.append(['Security Deposit', '', '', f"${booking.security_deposit}"])
    billing_data.append(['TOTAL', '', '', f"${booking.total_amount}"])
    
    billing_table = Table(billing_data)
    billing_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))
    
    story.append(billing_table)
    story.append(Spacer(1, 30))
    
    # Terms and conditions
    story.append(Paragraph("Terms and Conditions:", styles['Heading2']))
    terms = [
        "1. Vehicle must be returned with the same fuel level as at pickup.",
        "2. Any damage to the vehicle will be charged separately.",
        "3. Late return fees may apply for overdue rentals.",
        "4. Security deposit will be refunded after vehicle inspection.",
    ]
    
    for term in terms:
        story.append(Paragraph(term, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    
    # Return PDF response
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{booking.booking_number}.pdf"'
    
    return response
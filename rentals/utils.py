from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from io import BytesIO
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

def generate_booking_number():
    """Generate a unique booking number"""
    return f"AU{uuid.uuid4().hex[:8].upper()}"

def calculate_rental_days(start_date, end_date):
    """Calculate number of rental days"""
    if start_date and end_date:
        return max(1, (end_date - start_date).days)
    return 1

def calculate_total_amount(daily_rate, total_days, extras=None):
    """Calculate total rental amount including extras"""
    base_amount = Decimal(str(daily_rate)) * total_days
    
    if extras:
        for extra in extras:
            base_amount += Decimal(str(extra.get('price', 0)))
    
    return base_amount

def send_booking_confirmation_email(booking):
    """Send booking confirmation email to customer"""
    subject = f'Booking Confirmation - {booking.booking_number}'
    
    html_message = render_to_string('emails/booking_confirmation.html', {
        'booking': booking,
        'user': booking.user,
        'vehicle': booking.vehicle,
    })
    
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.user.email],
        html_message=html_message,
        fail_silently=False,
    )

def send_booking_reminder_email(booking):
    """Send booking reminder email 24 hours before pickup"""
    subject = f'Rental Reminder - Pickup Tomorrow - {booking.booking_number}'
    
    html_message = render_to_string('emails/booking_reminder.html', {
        'booking': booking,
        'user': booking.user,
        'vehicle': booking.vehicle,
    })
    
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.user.email],
        html_message=html_message,
        fail_silently=False,
    )

def generate_booking_invoice_pdf(booking):
    """Generate PDF invoice for booking"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Build PDF content
    story = []
    
    # Company header
    story.append(Paragraph("Aurora Motors Pty Ltd", title_style))
    story.append(Paragraph("Premium Car Rental Services", normal_style))
    story.append(Spacer(1, 20))
    
    # Invoice details
    story.append(Paragraph("RENTAL INVOICE", heading_style))
    story.append(Spacer(1, 12))
    
    # Create invoice details table
    invoice_data = [
        ['Invoice Number:', booking.booking_number],
        ['Invoice Date:', datetime.now().strftime('%d %B %Y')],
        ['Customer:', booking.user.get_full_name()],
        ['Email:', booking.user.email],
        ['Phone:', booking.user.userprofile.phone if hasattr(booking.user, 'userprofile') else 'N/A'],
    ]
    
    invoice_table = Table(invoice_data, colWidths=[2*72, 3*72])
    invoice_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(invoice_table)
    story.append(Spacer(1, 20))
    
    # Vehicle and rental details
    story.append(Paragraph("RENTAL DETAILS", heading_style))
    story.append(Spacer(1, 12))
    
    rental_data = [
        ['Vehicle:', booking.vehicle.display_name],
        ['License Plate:', booking.vehicle.license_plate],
        ['Pickup Date:', booking.start_date.strftime('%d %B %Y at %H:%M')],
        ['Return Date:', booking.end_date.strftime('%d %B %Y at %H:%M')],
        ['Pickup Location:', booking.pickup_location],
        ['Return Location:', booking.dropoff_location],
        ['Rental Days:', str(booking.total_days)],
    ]
    
    rental_table = Table(rental_data, colWidths=[2*72, 4*72])
    rental_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(rental_table)
    story.append(Spacer(1, 20))
    
    # Charges
    story.append(Paragraph("CHARGES", heading_style))
    story.append(Spacer(1, 12))
    
    charges_data = [
        ['Description', 'Days', 'Rate', 'Amount'],
        [booking.vehicle.display_name, str(booking.total_days), f'${booking.daily_rate}', f'${booking.total_amount}'],
        ['Security Deposit', '', '', f'${booking.security_deposit}'],
        ['Total Amount', '', '', f'${booking.total_amount + booking.security_deposit}'],
    ]
    
    charges_table = Table(charges_data, colWidths=[3*72, 1*72, 1*72, 1*72])
    charges_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    story.append(charges_table)
    story.append(Spacer(1, 30))
    
    # Terms and conditions
    story.append(Paragraph("TERMS AND CONDITIONS", heading_style))
    story.append(Spacer(1, 12))
    
    terms = [
        "• Security deposit will be refunded upon satisfactory return of vehicle",
        "• Vehicle must be returned with same fuel level as pickup",
        "• Late return charges apply at $50 per hour",
        "• Customer is responsible for all traffic fines and penalties",
        "• Full insurance coverage included with excess as specified",
    ]
    
    for term in terms:
        story.append(Paragraph(term, normal_style))
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("Thank you for choosing Aurora Motors!", normal_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def check_vehicle_availability(vehicle, start_date, end_date, exclude_booking=None):
    """Check if vehicle is available for given date range"""
    from .models import Booking
    
    overlapping_bookings = Booking.objects.filter(
        vehicle=vehicle,
        status__in=['confirmed', 'active'],
        start_date__lt=end_date,
        end_date__gt=start_date
    )
    
    if exclude_booking:
        overlapping_bookings = overlapping_bookings.exclude(id=exclude_booking.id)
    
    return not overlapping_bookings.exists()

def get_available_vehicles(start_date, end_date, category=None):
    """Get list of available vehicles for date range"""
    from .models import Vehicle, Booking
    
    # Get vehicles that are booked during the specified period
    booked_vehicle_ids = Booking.objects.filter(
        status__in=['confirmed', 'active'],
        start_date__lt=end_date,
        end_date__gt=start_date
    ).values_list('vehicle_id', flat=True)
    
    # Get available vehicles
    available_vehicles = Vehicle.objects.filter(
        status='available'
    ).exclude(id__in=booked_vehicle_ids)
    
    if category:
        available_vehicles = available_vehicles.filter(category=category)
    
    return available_vehicles

def calculate_late_fees(booking, actual_return_date):
    """Calculate late return fees"""
    if actual_return_date <= booking.end_date:
        return Decimal('0.00')
    
    # Calculate hours late
    late_duration = actual_return_date - booking.end_date
    late_hours = max(1, int(late_duration.total_seconds() / 3600))
    
    # $50 per hour late fee
    late_fee_per_hour = Decimal('50.00')
    total_late_fee = late_fee_per_hour * late_hours
    
    return total_late_fee

def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:,.2f}"

def validate_license_expiry(expiry_date):
    """Check if license is still valid"""
    return expiry_date > datetime.now().date()

def generate_contract_pdf(booking):
    """Generate rental contract PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    story = []
    
    # Contract header
    story.append(Paragraph("CAR RENTAL AGREEMENT", title_style))
    story.append(Spacer(1, 20))
    
    # Agreement details
    story.append(Paragraph("RENTAL AGREEMENT TERMS", heading_style))
    story.append(Paragraph(
        f"This rental agreement is entered into on {datetime.now().strftime('%d %B %Y')} "
        f"between Aurora Motors Pty Ltd ('Company') and {booking.user.get_full_name()} ('Renter').",
        normal_style
    ))
    story.append(Spacer(1, 12))
    
    # Vehicle information
    vehicle_info = f"""
    <b>VEHICLE INFORMATION</b><br/>
    Vehicle: {booking.vehicle.display_name}<br/>
    License Plate: {booking.vehicle.license_plate}<br/>
    VIN: {booking.vehicle.vin_number}<br/>
    """
    
    story.append(Paragraph(vehicle_info, normal_style))
    story.append(Spacer(1, 12))
    
    # Rental period
    rental_info = f"""
    <b>RENTAL PERIOD</b><br/>
    Pickup: {booking.start_date.strftime('%d %B %Y at %H:%M')}<br/>
    Return: {booking.end_date.strftime('%d %B %Y at %H:%M')}<br/>
    Pickup Location: {booking.pickup_location}<br/>
    Return Location: {booking.dropoff_location}<br/>
    """
    
    story.append(Paragraph(rental_info, normal_style))
    story.append(Spacer(1, 12))
    
    # Terms and conditions
    terms = """
    <b>TERMS AND CONDITIONS</b><br/>
    1. The Renter must be at least 21 years old with a valid driver's license.<br/>
    2. The vehicle must be returned in the same condition as received.<br/>
    3. The Renter is responsible for all traffic violations and fines.<br/>
    4. Smoking is prohibited in all vehicles.<br/>
    5. The security deposit will be refunded upon satisfactory return.<br/>
    6. Any damage to the vehicle will be charged to the Renter.<br/>
    7. The vehicle must be returned with the same fuel level.<br/>
    """
    
    story.append(Paragraph(terms, normal_style))
    story.append(Spacer(1, 30))
    
    # Signature section
    signature_info = f"""
    <b>AGREEMENT</b><br/>
    By signing below, the Renter acknowledges having read and agreed to all terms.<br/><br/>
    Customer Signature: ___________________________ Date: ___________<br/><br/>
    {booking.user.get_full_name()}<br/>
    Booking Number: {booking.booking_number}
    """
    
    story.append(Paragraph(signature_info, normal_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer
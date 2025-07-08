from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from .models import Booking, BookingExtension, BookingAdditionalDriver, BookingNote
from apps.vehicles.models import Vehicle

class BookingForm(forms.ModelForm):
    """Booking creation form"""
    
    pickup_location = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pickup location'
        })
    )
    
    return_location = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Return location'
        })
    )
    
    special_requests = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any special requests or requirements...'
        })
    )
    
    primary_driver_license = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Driver license number'
        })
    )
    
    insurance_selected = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = Booking
        fields = [
            'start_date', 'end_date', 'pickup_location', 'return_location',
            'special_requests', 'primary_driver_license', 'insurance_selected'
        ]
        widgets = {
            'start_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, vehicle=None, user=None, **kwargs):
        self.vehicle = vehicle
        self.user = user
        super().__init__(*args, **kwargs)
        
        # Set default locations if vehicle has location
        if self.vehicle and self.vehicle.location:
            self.fields['pickup_location'].initial = self.vehicle.location
            self.fields['return_location'].initial = self.vehicle.location
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            # Basic date validation
            if start_date >= end_date:
                raise ValidationError('End date must be after start date.')
            
            if start_date < timezone.now():
                raise ValidationError('Start date cannot be in the past.')
            
            # Minimum booking duration (1 hour)
            duration = end_date - start_date
            if duration.total_seconds() < 3600:
                raise ValidationError('Minimum booking duration is 1 hour.')
            
            # Check vehicle availability
            if self.vehicle:
                overlapping_bookings = Booking.objects.filter(
                    vehicle=self.vehicle,
                    status__in=['confirmed', 'active'],
                    start_date__lt=end_date,
                    end_date__gt=start_date
                )
                
                if self.instance.pk:
                    overlapping_bookings = overlapping_bookings.exclude(pk=self.instance.pk)
                
                if overlapping_bookings.exists():
                    raise ValidationError('Vehicle is not available for the selected dates.')
        
        return cleaned_data
    
    def save(self, commit=True):
        booking = super().save(commit=False)
        booking.vehicle = self.vehicle
        booking.user = self.user
        
        if commit:
            booking.save()
        
        return booking


class BookingUpdateForm(forms.ModelForm):
    """Booking update form for staff"""
    
    class Meta:
        model = Booking
        fields = [
            'start_date', 'end_date', 'pickup_location', 'return_location',
            'status', 'special_requests', 'internal_notes', 'pickup_mileage',
            'return_mileage'
        ]
        widgets = {
            'start_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'pickup_location': forms.TextInput(attrs={'class': 'form-control'}),
            'return_location': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'internal_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'pickup_mileage': forms.NumberInput(attrs={'class': 'form-control'}),
            'return_mileage': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class BookingCancellationForm(forms.Form):
    """Booking cancellation form"""
    
    reason = forms.ChoiceField(
        choices=Booking.CANCELLATION_REASONS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Additional notes about the cancellation...'
        })
    )
    
    confirm_cancellation = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class BookingExtensionForm(forms.ModelForm):
    """Booking extension request form"""
    
    class Meta:
        model = BookingExtension
        fields = ['new_end_date', 'reason']
        widgets = {
            'new_end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Please explain why you need to extend your booking...'
            })
        }
    
    def __init__(self, *args, booking=None, **kwargs):
        self.booking = booking
        super().__init__(*args, **kwargs)
        
        if self.booking:
            # Set minimum date to current end date
            self.fields['new_end_date'].widget.attrs['min'] = self.booking.end_date.strftime('%Y-%m-%dT%H:%M')
    
    def clean_new_end_date(self):
        new_end_date = self.cleaned_data.get('new_end_date')
        
        if new_end_date and self.booking:
            if new_end_date <= self.booking.end_date:
                raise ValidationError('New end date must be after the current end date.')
            
            # Check vehicle availability for extended period
            overlapping_bookings = Booking.objects.filter(
                vehicle=self.booking.vehicle,
                status__in=['confirmed', 'active'],
                start_date__lt=new_end_date,
                end_date__gt=self.booking.end_date
            ).exclude(pk=self.booking.pk)
            
            if overlapping_bookings.exists():
                raise ValidationError('Vehicle is not available for the extended period.')
        
        return new_end_date
    
    def save(self, commit=True):
        extension = super().save(commit=False)
        extension.booking = self.booking
        extension.original_end_date = self.booking.end_date
        
        # Calculate additional days and amount
        additional_days = (extension.new_end_date.date() - self.booking.end_date.date()).days
        extension.additional_days = additional_days
        extension.additional_amount = self.booking.vehicle.get_rate_for_duration(additional_days)
        
        if commit:
            extension.save()
        
        return extension


class AdditionalDriverForm(forms.ModelForm):
    """Additional driver form"""
    
    class Meta:
        model = BookingAdditionalDriver
        fields = ['driver', 'license_number', 'license_expiry']
        widgets = {
            'driver': forms.Select(attrs={'class': 'form-select'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'license_expiry': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, booking=None, **kwargs):
        self.booking = booking
        super().__init__(*args, **kwargs)
        
        # Exclude the primary booking user from additional drivers
        if self.booking:
            self.fields['driver'].queryset = self.fields['driver'].queryset.exclude(
                id=self.booking.user.id
            )
    
    def clean_license_expiry(self):
        license_expiry = self.cleaned_data.get('license_expiry')
        
        if license_expiry and license_expiry <= timezone.now().date():
            raise ValidationError('License must be valid (not expired).')
        
        return license_expiry


class BookingNoteForm(forms.ModelForm):
    """Booking note form"""
    
    class Meta:
        model = BookingNote
        fields = ['content', 'is_important']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Add a note about this booking...'
            }),
            'is_important': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


class BookingSearchForm(forms.Form):
    """Booking search form"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by booking number, customer name, or vehicle...'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + list(Booking.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    vehicle = forms.ModelChoiceField(
        required=False,
        queryset=Vehicle.objects.filter(is_active=True),
        empty_label="All Vehicles",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class VehiclePickupForm(forms.Form):
    """Vehicle pickup form"""
    
    pickup_mileage = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current vehicle mileage'
        })
    )
    
    vehicle_condition_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Note any existing damage or issues...'
        })
    )
    
    customer_signature = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    staff_signature = forms.CharField(
        widget=forms.HiddenInput()
    )


class VehicleReturnForm(forms.Form):
    """Vehicle return form"""
    
    return_mileage = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Vehicle mileage at return'
        })
    )
    
    fuel_level = forms.ChoiceField(
        choices=[
            ('full', 'Full'),
            ('3/4', '3/4'),
            ('1/2', '1/2'),
            ('1/4', '1/4'),
            ('empty', 'Empty'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    vehicle_condition = forms.ChoiceField(
        choices=[
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('fair', 'Fair - Minor Issues'),
            ('poor', 'Poor - Significant Issues'),
            ('damaged', 'Damaged'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    damage_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe any new damage or issues...'
        })
    )
    
    additional_charges = forms.DecimalField(
        required=False,
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00'
        })
    )
    
    customer_signature = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    staff_signature = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def clean(self):
        cleaned_data = super().clean()
        vehicle_condition = cleaned_data.get('vehicle_condition')
        damage_notes = cleaned_data.get('damage_notes')
        
        if vehicle_condition in ['fair', 'poor', 'damaged'] and not damage_notes:
            raise ValidationError('Damage notes are required when vehicle condition is not excellent or good.')
        
        return cleaned_data
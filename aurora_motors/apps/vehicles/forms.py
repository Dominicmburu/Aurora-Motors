from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Vehicle, VehicleImage, VehicleReview, VehicleMaintenanceRecord

class VehicleForm(forms.ModelForm):
    """Vehicle creation/edit form"""
    
    class Meta:
        model = Vehicle
        fields = [
            'name', 'brand', 'category', 'model', 'year', 'transmission',
            'fuel_type', 'engine_size', 'seats', 'doors', 'registration_number',
            'vin', 'color', 'mileage', 'condition', 'daily_rate', 'weekly_rate',
            'monthly_rate', 'security_deposit', 'status', 'is_featured',
            'is_active', 'description', 'location', 'insurance_company',
            'insurance_policy', 'insurance_expiry', 'last_service_date',
            'next_service_date', 'last_service_mileage', 'next_service_mileage'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'insurance_expiry': forms.DateInput(attrs={'type': 'date'}),
            'last_service_date': forms.DateInput(attrs={'type': 'date'}),
            'next_service_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput, 
                                       forms.DateInput, forms.Select, forms.Textarea)):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
    
    def clean_year(self):
        year = self.cleaned_data.get('year')
        current_year = timezone.now().year
        if year > current_year + 1:
            raise ValidationError('Year cannot be more than one year in the future.')
        return year
    
    def clean_vin(self):
        vin = self.cleaned_data.get('vin')
        if vin and len(vin) != 17:
            raise ValidationError('VIN must be exactly 17 characters long.')
        return vin.upper() if vin else vin
    
    def clean(self):
        cleaned_data = super().clean()
        weekly_rate = cleaned_data.get('weekly_rate')
        monthly_rate = cleaned_data.get('monthly_rate')
        daily_rate = cleaned_data.get('daily_rate')
        
        # Validate rate consistency
        if weekly_rate and daily_rate:
            if weekly_rate > daily_rate * 7:
                raise ValidationError('Weekly rate should not exceed daily rate × 7.')
        
        if monthly_rate and daily_rate:
            if monthly_rate > daily_rate * 30:
                raise ValidationError('Monthly rate should not exceed daily rate × 30.')
        
        return cleaned_data


class VehicleImageForm(forms.ModelForm):
    """Vehicle image form"""
    
    class Meta:
        model = VehicleImage
        fields = ['image', 'caption', 'is_primary', 'sort_order']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class VehicleReviewForm(forms.ModelForm):
    """Vehicle review form"""
    
    class Meta:
        model = VehicleReview
        fields = [
            'rating', 'title', 'content', 'cleanliness_rating',
            'comfort_rating', 'performance_rating'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'rating': forms.Select(
                choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
                attrs={'class': 'form-select'}
            ),
            'cleanliness_rating': forms.Select(
                choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
                attrs={'class': 'form-select'}
            ),
            'comfort_rating': forms.Select(
                choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
                attrs={'class': 'form-select'}
            ),
            'performance_rating': forms.Select(
                choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
                attrs={'class': 'form-select'}
            ),
        }


class VehicleMaintenanceForm(forms.ModelForm):
    """Vehicle maintenance record form"""
    
    class Meta:
        model = VehicleMaintenanceRecord
        fields = [
            'maintenance_type', 'description', 'cost', 'mileage_at_service',
            'service_date', 'next_service_date', 'next_service_mileage',
            'service_provider', 'service_provider_contact', 'invoice_number',
            'notes'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'service_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'next_service_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'


class VehicleSearchForm(forms.Form):
    """Vehicle search form"""
    
    pickup_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'required': True
        })
    )
    
    return_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'required': True
        })
    )
    
    pickup_location = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pickup location'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        pickup_date = cleaned_data.get('pickup_date')
        return_date = cleaned_data.get('return_date')
        
        if pickup_date and return_date:
            if pickup_date >= return_date:
                raise ValidationError('Return date must be after pickup date.')
            
            if pickup_date < timezone.now().date():
                raise ValidationError('Pickup date cannot be in the past.')
        
        return cleaned_data


class VehicleAvailabilityForm(forms.Form):
    """Check vehicle availability form"""
    
    start_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        })
    )
    
    end_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError('End date must be after start date.')
            
            if start_date < timezone.now():
                raise ValidationError('Start date cannot be in the past.')
            
            # Check minimum booking duration (e.g., 1 hour)
            duration = end_date - start_date
            if duration.total_seconds() < 3600:  # 1 hour in seconds
                raise ValidationError('Minimum booking duration is 1 hour.')
        
        return cleaned_data
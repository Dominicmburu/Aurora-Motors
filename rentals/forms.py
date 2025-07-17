from datetime import timezone
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import *

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'start_date', 'end_date', 'pickup_location', 
            'dropoff_location', 'special_requests'
        ]
        widgets = {
            'start_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'end_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'pickup_location': forms.Select(attrs={'class': 'form-control'}),
            'dropoff_location': forms.Select(attrs={'class': 'form-control'}),
            'special_requests': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Any special requirements?'}
            ),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError("End date must be after start date")
            
            if start_date < timezone.now():
                raise forms.ValidationError("Start date cannot be in the past")
            
            # Minimum rental period of 1 day
            if (end_date - start_date).days < 1:
                raise forms.ValidationError("Minimum rental period is 1 day")
        
        return cleaned_data

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'phone', 'date_of_birth', 'address', 'city', 'state', 
            'postal_code', 'license_number', 'license_expiry', 
            'license_image', 'id_document', 'emergency_contact_name', 
            'emergency_contact_phone'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'license_expiry': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class ContractSigningForm(forms.Form):
    signature = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    agree_terms = forms.BooleanField(
        required=True,
        label="I agree to the terms and conditions"
    )
    
class VehicleSearchForm(forms.Form):
    pickup_location = forms.ModelChoiceField(
        queryset=Location.objects.filter(is_active=True),
        empty_label="Select pickup location",
        required=True
    )
    dropoff_location = forms.ModelChoiceField(
        queryset=Location.objects.filter(is_active=True),
        empty_label="Select drop-off location",
        required=True
    )
    pickup_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=True
    )
    dropoff_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=True
    )
    vehicle_type = forms.ModelChoiceField(
        queryset=VehicleCategory.objects.all(),
        empty_label="Any vehicle type",
        required=False
    )
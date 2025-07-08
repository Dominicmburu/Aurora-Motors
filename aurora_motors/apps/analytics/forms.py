from django import forms
from django.core.exceptions import ValidationError
from .models import Report, Dashboard, KPI
import json
from .models import AnalyticsEvent

class ReportForm(forms.ModelForm):
    """Report creation/edit form"""
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = Report
        fields = [
            'name', 'report_type', 'description', 'is_scheduled',
            'schedule_frequency', 'is_public'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'is_scheduled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'schedule_frequency': forms.Select(attrs={'class': 'form-select'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pre-populate filters if editing existing report
        if self.instance.pk and self.instance.filters:
            filters = self.instance.filters
            self.fields['date_from'].initial = filters.get('date_from')
            self.fields['date_to'].initial = filters.get('date_to')
    
    def clean(self):
        cleaned_data = super().clean()
        is_scheduled = cleaned_data.get('is_scheduled')
        schedule_frequency = cleaned_data.get('schedule_frequency')
        
        if is_scheduled and not schedule_frequency:
            raise ValidationError('Schedule frequency is required for scheduled reports.')
        
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from >= date_to:
            raise ValidationError('End date must be after start date.')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Build filters from form data
        filters = {}
        if self.cleaned_data.get('date_from'):
            filters['date_from'] = self.cleaned_data['date_from'].isoformat()
        if self.cleaned_data.get('date_to'):
            filters['date_to'] = self.cleaned_data['date_to'].isoformat()
        
        instance.filters = filters
        
        if commit:
            instance.save()
        
        return instance


class DashboardForm(forms.ModelForm):
    """Dashboard creation/edit form"""
    
    class Meta:
        model = Dashboard
        fields = ['name', 'description', 'is_default', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class KPIForm(forms.ModelForm):
    """KPI creation/edit form"""
    
    class Meta:
        model = KPI
        fields = [
            'name', 'description', 'calculation_method', 'target_value',
            'update_frequency', 'unit', 'format_type', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'calculation_method': forms.Select(attrs={'class': 'form-select'}),
            'target_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'update_frequency': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'format_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AnalyticsFilterForm(forms.Form):
    """Analytics filtering form"""
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + list(AnalyticsEvent.EVENT_CATEGORIES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    action = forms.ChoiceField(
        required=False,
        choices=[('', 'All Actions')] + list(AnalyticsEvent.EVENT_ACTIONS),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    user_type = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Users'),
            ('customer', 'Customers'),
            ('staff', 'Staff'),
            ('admin', 'Admins'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class CustomReportForm(forms.Form):
    """Custom report builder form"""
    
    CHART_TYPES = [
        ('line', 'Line Chart'),
        ('bar', 'Bar Chart'),
        ('pie', 'Pie Chart'),
        ('area', 'Area Chart'),
        ('scatter', 'Scatter Plot'),
        ('table', 'Data Table'),
    ]
    
    report_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    data_source = forms.ChoiceField(
        choices=[
            ('bookings', 'Bookings'),
            ('users', 'Users'),
            ('vehicles', 'Vehicles'),
            ('documents', 'Documents'),
            ('contracts', 'Contracts'),
            ('analytics_events', 'Analytics Events'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    chart_type = forms.ChoiceField(
        choices=CHART_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_range = forms.ChoiceField(
        choices=[
            ('7d', 'Last 7 days'),
            ('30d', 'Last 30 days'),
            ('90d', 'Last 90 days'),
            ('1y', 'Last year'),
            ('custom', 'Custom range'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    custom_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    custom_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    group_by = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'No grouping'),
            ('day', 'By day'),
            ('week', 'By week'),
            ('month', 'By month'),
            ('year', 'By year'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_range = cleaned_data.get('date_range')
        custom_date_from = cleaned_data.get('custom_date_from')
        custom_date_to = cleaned_data.get('custom_date_to')
        
        if date_range == 'custom':
            if not custom_date_from or not custom_date_to:
                raise ValidationError('Custom date range requires both start and end dates.')
            if custom_date_from >= custom_date_to:
                raise ValidationError('End date must be after start date.')
        
        return cleaned_data
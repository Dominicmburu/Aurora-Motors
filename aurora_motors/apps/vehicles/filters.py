import django_filters
from django import forms
from .models import Vehicle, VehicleCategory, VehicleBrand
from .choices import TRANSMISSION_CHOICES, FUEL_TYPE_CHOICES

class VehicleFilter(django_filters.FilterSet):
    """Vehicle filter for search functionality"""
    
    search = django_filters.CharFilter(
        method='filter_search',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search vehicles...'
        })
    )
    
    category = django_filters.ModelChoiceFilter(
        queryset=VehicleCategory.objects.filter(is_active=True),
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    brand = django_filters.ModelChoiceFilter(
        queryset=VehicleBrand.objects.filter(is_active=True),
        empty_label="All Brands",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    transmission = django_filters.ChoiceFilter(
        choices=[('', 'All Transmissions')] + list(TRANSMISSION_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fuel_type = django_filters.ChoiceFilter(
        choices=[('', 'All Fuel Types')] + list(FUEL_TYPE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    min_price = django_filters.NumberFilter(
        field_name='daily_rate',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price'
        })
    )
    
    max_price = django_filters.NumberFilter(
        field_name='daily_rate',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price'
        })
    )
    
    min_year = django_filters.NumberFilter(
        field_name='year',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min year'
        })
    )
    
    max_year = django_filters.NumberFilter(
        field_name='year',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max year'
        })
    )
    
    seats = django_filters.ChoiceFilter(
        choices=[
            ('', 'Any seats'),
            ('2', '2 seats'),
            ('4', '4 seats'),
            ('5', '5 seats'),
            ('7', '7+ seats'),
        ],
        method='filter_seats',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    doors = django_filters.ChoiceFilter(
        choices=[
            ('', 'Any doors'),
            ('2', '2 doors'),
            ('4', '4 doors'),
            ('5', '5 doors'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Vehicle
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Custom search filter"""
        if value:
            return queryset.filter(
                models.Q(name__icontains=value) |
                models.Q(brand__name__icontains=value) |
                models.Q(model__icontains=value) |
                models.Q(category__name__icontains=value) |
                models.Q(description__icontains=value)
            )
        return queryset
    
    def filter_seats(self, queryset, name, value):
        """Custom seats filter"""
        if value == '7':
            return queryset.filter(seats__gte=7)
        elif value:
            return queryset.filter(seats=value)
        return queryset


class AvailabilityFilter(django_filters.FilterSet):
    """Filter for checking vehicle availability"""
    
    start_date = django_filters.DateFilter(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    end_date = django_filters.DateFilter(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    location = django_filters.CharFilter(
        field_name='location',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pickup location'
        })
    )
    
    class Meta:
        model = Vehicle
        fields = ['start_date', 'end_date', 'location']
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ContractTemplate, Contract, ContractSignature

class ContractTemplateForm(forms.ModelForm):
    """Contract template form"""
    
    class Meta:
        model = ContractTemplate
        fields = [
            'name', 'template_type', 'version', 'content', 'is_active',
            'is_required', 'requires_signature', 'requires_witness', 'requires_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'template_type': forms.Select(attrs={'class': 'form-select'}),
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 20,
                'id': 'contract-editor'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_signature': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_witness': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_date': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text for content field
        self.fields['content'].help_text = (
            "Use the following variables in your template:<br>"
            "{{customer_name}} - Customer full name<br>"
            "{{customer_email}} - Customer email<br>"
            "{{booking_number}} - Booking number<br>"
            "{{vehicle_name}} - Vehicle name<br>"
            "{{start_date}} - Rental start date<br>"
            "{{end_date}} - Rental end date<br>"
            "{{total_amount}} - Total booking amount<br>"
            "{{current_date}} - Current date"
        )


class ContractForm(forms.ModelForm):
    """Contract creation/edit form"""
    
    expires_in_days = forms.IntegerField(
        min_value=1,
        max_value=30,
        initial=7,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Number of days before contract expires"
    )
    
    class Meta:
        model = Contract
        fields = ['title', 'content', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'readonly': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Internal notes about this contract...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make content readonly for editing
        if self.instance.pk:
            self.fields['content'].widget.attrs['readonly'] = True


class ContractSignatureForm(forms.Form):
    """Contract signature form"""
    
    SIGNATURE_METHODS = (
        ('draw', 'Draw Signature'),
        ('type', 'Type Signature'),
        ('upload', 'Upload Signature'),
    )
    
    signature_method = forms.ChoiceField(
        choices=SIGNATURE_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='draw'
    )
    
    signature_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    typed_signature = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control signature-input',
            'placeholder': 'Type your full name here'
        })
    )
    
    signature_file = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    agree_to_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    confirm_identity = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        signature_method = cleaned_data.get('signature_method')
        signature_data = cleaned_data.get('signature_data')
        typed_signature = cleaned_data.get('typed_signature')
        signature_file = cleaned_data.get('signature_file')
        
        # Validate signature based on method
        if signature_method == 'draw' and not signature_data:
            raise ValidationError('Please draw your signature.')
        elif signature_method == 'type' and not typed_signature:
            raise ValidationError('Please type your signature.')
        elif signature_method == 'upload' and not signature_file:
            raise ValidationError('Please upload your signature image.')
        
        return cleaned_data


class ContractSearchForm(forms.Form):
    """Contract search form"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search contracts...'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + list(Contract.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    template_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(ContractTemplate.TEMPLATE_TYPES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
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


class BulkContractCreateForm(forms.Form):
    """Form for creating multiple contracts from bookings"""
    
    template = forms.ModelChoiceField(
        queryset=ContractTemplate.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select a template"
    )
    
    bookings = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple(),
        required=True
    )
    
    expires_in_days = forms.IntegerField(
        min_value=1,
        max_value=30,
        initial=7,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    send_immediately = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        bookings_queryset = kwargs.pop('bookings_queryset', None)
        super().__init__(*args, **kwargs)
        
        if bookings_queryset:
            self.fields['bookings'].queryset = bookings_queryset


class ContractReminderForm(forms.Form):
    """Contract reminder form"""
    
    reminder_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        })
    )
    
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Reminder email subject'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Reminder message...'
        })
    )
    
    def clean_reminder_date(self):
        reminder_date = self.cleaned_data.get('reminder_date')
        
        if reminder_date and reminder_date <= timezone.now():
            raise ValidationError('Reminder date must be in the future.')
        
        return reminder_date


class ContractRevisionForm(forms.Form):
    """Contract revision form"""
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 15,
            'id': 'revision-editor'
        })
    )
    
    change_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe the changes made...'
        })
    )
    
    notify_customer = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
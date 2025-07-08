from datetime import timezone
from django import forms
from django.core.exceptions import ValidationError
from .models import Notification, NotificationTemplate, NotificationPreference, NotificationChannel

class NotificationTemplateForm(forms.ModelForm):
    """Notification template form"""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'template_type', 'trigger_type', 'subject', 'email_body',
            'email_html_body', 'sms_body', 'push_title', 'push_body',
            'in_app_title', 'in_app_body', 'is_active', 'is_required'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'template_type': forms.Select(attrs={'class': 'form-select'}),
            'trigger_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'email_body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8
            }),
            'email_html_body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10
            }),
            'sms_body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'maxlength': 160
            }),
            'push_title': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 100
            }),
            'push_body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'in_app_title': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 100
            }),
            'in_app_body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text for template variables
        help_text = """
        Available variables:<br>
        {{user_name}} - User's full name<br>
        {{user_email}} - User's email<br>
        {{booking_number}} - Booking number<br>
        {{vehicle_name}} - Vehicle name<br>
        {{start_date}} - Start date<br>
        {{end_date}} - End date<br>
        {{total_amount}} - Total amount<br>
        {{company_name}} - Company name<br>
        {{site_url}} - Website URL
        """
        
        for field in ['email_body', 'email_html_body', 'sms_body', 'push_body', 'in_app_body']:
            if field in self.fields:
                self.fields[field].help_text = help_text
    
    def clean(self):
        cleaned_data = super().clean()
        template_type = cleaned_data.get('template_type')
        
        # Validate required fields based on template type
        if template_type == 'email':
            if not cleaned_data.get('subject'):
                raise ValidationError('Subject is required for email templates.')
            if not cleaned_data.get('email_body'):
                raise ValidationError('Email body is required for email templates.')
        elif template_type == 'sms':
            if not cleaned_data.get('sms_body'):
                raise ValidationError('SMS body is required for SMS templates.')
        elif template_type == 'push':
            if not cleaned_data.get('push_title') or not cleaned_data.get('push_body'):
                raise ValidationError('Title and body are required for push notifications.')
        elif template_type == 'in_app':
            if not cleaned_data.get('in_app_title') or not cleaned_data.get('in_app_body'):
                raise ValidationError('Title and body are required for in-app notifications.')
        
        return cleaned_data


class NotificationPreferenceForm(forms.ModelForm):
    """Notification preference form"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'email_booking_confirmations', 'email_booking_reminders',
            'email_contract_notifications', 'email_document_notifications',
            'email_marketing', 'sms_enabled', 'sms_booking_reminders',
            'sms_urgent_notifications', 'push_enabled', 'push_booking_updates',
            'push_document_updates', 'in_app_enabled', 'in_app_all_notifications',
            'digest_frequency', 'quiet_hours_enabled', 'quiet_hours_start',
            'quiet_hours_end'
        ]
        widgets = {
            'email_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_booking_confirmations': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_booking_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_contract_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_document_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_marketing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_booking_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_urgent_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_booking_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_document_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'in_app_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'in_app_all_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'digest_frequency': forms.Select(attrs={'class': 'form-select'}),
            'quiet_hours_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'quiet_hours_start': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),
            'quiet_hours_end': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        quiet_hours_enabled = cleaned_data.get('quiet_hours_enabled')
        quiet_hours_start = cleaned_data.get('quiet_hours_start')
        quiet_hours_end = cleaned_data.get('quiet_hours_end')
        
        if quiet_hours_enabled:
            if not quiet_hours_start or not quiet_hours_end:
                raise ValidationError(
                    'Start and end times are required when quiet hours are enabled.'
                )
        
        return cleaned_data


class NotificationChannelForm(forms.ModelForm):
    """Notification channel form"""
    
    class Meta:
        model = NotificationChannel
        fields = [
            'name', 'channel_type', 'is_active', 'is_default',
            'rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'channel_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'rate_limit_per_minute': forms.NumberInput(attrs={'class': 'form-control'}),
            'rate_limit_per_hour': forms.NumberInput(attrs={'class': 'form-control'}),
            'rate_limit_per_day': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    # Dynamic config fields based on channel type
    smtp_host = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    smtp_port = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    smtp_username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    smtp_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    smtp_use_tls = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    sms_api_key = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    sms_api_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    sms_sender_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    webhook_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control'})
    )
    webhook_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pre-populate config fields if editing existing channel
        if self.instance.pk and self.instance.config:
            config = self.instance.config
            
            # Email config
            if self.instance.channel_type == 'email':
                self.fields['smtp_host'].initial = config.get('smtp_host', '')
                self.fields['smtp_port'].initial = config.get('smtp_port', 587)
                self.fields['smtp_username'].initial = config.get('smtp_username', '')
                self.fields['smtp_password'].initial = config.get('smtp_password', '')
                self.fields['smtp_use_tls'].initial = config.get('smtp_use_tls', True)
            
            # SMS config
            elif self.instance.channel_type == 'sms':
                self.fields['sms_api_key'].initial = config.get('api_key', '')
                self.fields['sms_api_secret'].initial = config.get('api_secret', '')
                self.fields['sms_sender_id'].initial = config.get('sender_id', '')
            
            # Webhook config
            elif self.instance.channel_type == 'webhook':
                self.fields['webhook_url'].initial = config.get('url', '')
                self.fields['webhook_secret'].initial = config.get('secret', '')
    
    def clean(self):
        cleaned_data = super().clean()
        channel_type = cleaned_data.get('channel_type')
        
        # Validate required fields based on channel type
        if channel_type == 'email':
            required_fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password']
            for field in required_fields:
                if not cleaned_data.get(field):
                    raise ValidationError(f'{field.replace("_", " ").title()} is required for email channels.')
        
        elif channel_type == 'sms':
            required_fields = ['sms_api_key', 'sms_api_secret']
            for field in required_fields:
                if not cleaned_data.get(field):
                    raise ValidationError(f'{field.replace("_", " ").title()} is required for SMS channels.')
        
        elif channel_type == 'webhook':
            if not cleaned_data.get('webhook_url'):
                raise ValidationError('Webhook URL is required for webhook channels.')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Build config based on channel type
        config = {}
        channel_type = self.cleaned_data.get('channel_type')
        
        if channel_type == 'email':
            config = {
                'smtp_host': self.cleaned_data.get('smtp_host', ''),
                'smtp_port': self.cleaned_data.get('smtp_port', 587),
                'smtp_username': self.cleaned_data.get('smtp_username', ''),
                'smtp_password': self.cleaned_data.get('smtp_password', ''),
                'smtp_use_tls': self.cleaned_data.get('smtp_use_tls', True),
            }
        elif channel_type == 'sms':
            config = {
                'api_key': self.cleaned_data.get('sms_api_key', ''),
                'api_secret': self.cleaned_data.get('sms_api_secret', ''),
                'sender_id': self.cleaned_data.get('sms_sender_id', ''),
            }
        elif channel_type == 'webhook':
            config = {
                'url': self.cleaned_data.get('webhook_url', ''),
                'secret': self.cleaned_data.get('webhook_secret', ''),
            }
        
        instance.config = config
        
        if commit:
            instance.save()
        
        return instance


class BulkNotificationForm(forms.Form):
    """Bulk notification sending form"""
    
    template = forms.ModelChoiceField(
        queryset=NotificationTemplate.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select a template"
    )
    
    recipients = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple(),
        required=True
    )
    
    send_immediately = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    scheduled_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        })
    )
    
    def __init__(self, *args, **kwargs):
        recipients_queryset = kwargs.pop('recipients_queryset', None)
        super().__init__(*args, **kwargs)
        
        if recipients_queryset:
            self.fields['recipients'].queryset = recipients_queryset
        else:
            from apps.accounts.models import CustomUser
            self.fields['recipients'].queryset = CustomUser.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        send_immediately = cleaned_data.get('send_immediately')
        scheduled_at = cleaned_data.get('scheduled_at')
        
        if not send_immediately and not scheduled_at:
            raise ValidationError('Please select immediate sending or provide a scheduled time.')
        
        if scheduled_at and scheduled_at <= timezone.now():
            raise ValidationError('Scheduled time must be in the future.')
        
        return cleaned_data


class NotificationTestForm(forms.Form):
    """Form for testing notification templates"""
    
    template = forms.ModelChoiceField(
        queryset=NotificationTemplate.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    test_recipient = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'test@example.com'
        })
    )
    
    # Test context variables
    user_name = forms.CharField(
        initial='John Doe',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    booking_number = forms.CharField(
        initial='BK2025123456',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    vehicle_name = forms.CharField(
        initial='Toyota Camry 2023',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    total_amount = forms.DecimalField(
        initial=250.00,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )


class NotificationSearchForm(forms.Form):
    """Notification search form"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search notifications...'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + list(Notification.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    template_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(NotificationTemplate.TEMPLATE_TYPES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        required=False,
        choices=[('', 'All Priorities')] + list(Notification.PRIORITY_CHOICES),
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
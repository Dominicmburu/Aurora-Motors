from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Document, DocumentCategory, DocumentShare, DocumentTemplate
import os

class DocumentUploadForm(forms.ModelForm):
    """Document upload form"""
    
    class Meta:
        model = Document
        fields = [
            'category', 'document_type', 'name', 'description', 'file',
            'issue_date', 'expiry_date', 'issuing_authority', 'document_number'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Document name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of the document...'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'
            }),
            'issue_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'expiry_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'issuing_authority': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., DMV, Passport Office'
            }),
            'document_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Document ID/Reference number'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter active categories
        self.fields['category'].queryset = DocumentCategory.objects.filter(is_active=True)
        
        # Set required fields based on document type
        self.fields['name'].required = True
        self.fields['file'].required = True
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('File size cannot exceed 10MB.')
            
            # Check file extension
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError(
                    f'File type {file_extension} is not allowed. '
                    f'Allowed types: {", ".join(allowed_extensions)}'
                )
        
        return file
    
    def clean(self):
        cleaned_data = super().clean()
        issue_date = cleaned_data.get('issue_date')
        expiry_date = cleaned_data.get('expiry_date')
        
        # Validate dates
        if issue_date and expiry_date:
            if issue_date >= expiry_date:
                raise ValidationError('Expiry date must be after issue date.')
        
        # Check if expiry date is in the past for new documents
        if expiry_date and expiry_date < timezone.now().date():
            raise ValidationError('Cannot upload a document that is already expired.')
        
        return cleaned_data


class DocumentUpdateForm(forms.ModelForm):
    """Document update form (without file upload)"""
    
    class Meta:
        model = Document
        fields = [
            'name', 'description', 'issue_date', 'expiry_date',
            'issuing_authority', 'document_number'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'issue_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'expiry_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'issuing_authority': forms.TextInput(attrs={'class': 'form-control'}),
            'document_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class DocumentReviewForm(forms.ModelForm):
    """Document review form for staff"""
    
    action = forms.ChoiceField(
        choices=[
            ('approve', 'Approve'),
            ('reject', 'Reject'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Document
        fields = ['review_notes']
        widgets = {
            'review_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Review notes and comments...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add rejection reason field
        self.fields['rejection_reason'] = forms.CharField(
            required=False,
            widget=forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for rejection (required if rejecting)...'
            })
        )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if action == 'reject' and not rejection_reason:
            raise ValidationError('Rejection reason is required when rejecting a document.')
        
        return cleaned_data


class DocumentShareForm(forms.ModelForm):
    """Document sharing form"""
    
    class Meta:
        model = DocumentShare
        fields = ['shared_with', 'access_type', 'expires_at']
        widgets = {
            'shared_with': forms.Select(attrs={'class': 'form-select'}),
            'access_type': forms.Select(attrs={'class': 'form-select'}),
            'expires_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Exclude the current user from sharing options
        if user:
            from apps.accounts.models import CustomUser
            self.fields['shared_with'].queryset = CustomUser.objects.exclude(
                id=user.id
            ).filter(is_active=True)
    
    def clean_expires_at(self):
        expires_at = self.cleaned_data.get('expires_at')
        
        if expires_at and expires_at <= timezone.now():
            raise ValidationError('Expiry date must be in the future.')
        
        return expires_at


class DocumentCategoryForm(forms.ModelForm):
    """Document category form"""
    
    allowed_extensions_text = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'pdf,jpg,png,doc,docx (comma-separated)'
        }),
        help_text="Enter allowed file extensions separated by commas"
    )
    
    class Meta:
        model = DocumentCategory
        fields = [
            'name', 'description', 'is_required', 'is_active',
            'sort_order', 'max_file_size'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_file_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1024,
                'step': 1024
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial value for allowed extensions
        if self.instance.pk and self.instance.allowed_extensions:
            self.fields['allowed_extensions_text'].initial = ','.join(
                self.instance.allowed_extensions
            )
    
    def clean_allowed_extensions_text(self):
        extensions_text = self.cleaned_data.get('allowed_extensions_text')
        
        if extensions_text:
            # Clean and validate extensions
            extensions = [ext.strip().lower() for ext in extensions_text.split(',')]
            extensions = [ext for ext in extensions if ext]  # Remove empty strings
            
            # Validate each extension
            valid_extensions = [
                'pdf', 'doc', 'docx', 'txt', 'rtf',  # Documents
                'jpg', 'jpeg', 'png', 'gif', 'bmp',  # Images
                'mp4', 'avi', 'mov', 'wmv',  # Videos
                'zip', 'rar', '7z'  # Archives
            ]
            
            for ext in extensions:
                if ext not in valid_extensions:
                    raise ValidationError(
                        f'Extension "{ext}" is not allowed. '
                        f'Valid extensions: {", ".join(valid_extensions)}'
                    )
            
            return extensions
        
        return []
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set allowed_extensions from the text field
        extensions_text = self.cleaned_data.get('allowed_extensions_text')
        if extensions_text:
            instance.allowed_extensions = [
                ext.strip().lower() for ext in extensions_text.split(',')
                if ext.strip()
            ]
        else:
            instance.allowed_extensions = []
        
        if commit:
            instance.save()
        
        return instance


class DocumentSearchForm(forms.Form):
    """Document search form"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search documents...'
        })
    )
    
    document_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(Document.DOCUMENT_TYPES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        required=False,
        queryset=DocumentCategory.objects.filter(is_active=True),
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + list(Document.STATUS_CHOICES),
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
    
    expiring_soon = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Show documents expiring within 30 days"
    )


class BulkDocumentActionForm(forms.Form):
    """Bulk document actions form"""
    
    ACTION_CHOICES = [
        ('approve', 'Approve Selected'),
        ('reject', 'Reject Selected'),
        ('delete', 'Delete Selected'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    documents = forms.ModelMultipleChoiceField(
        queryset=Document.objects.none(),
        widget=forms.CheckboxSelectMultiple()
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Notes for this action...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop('queryset', Document.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['documents'].queryset = queryset


class DocumentVersionUploadForm(forms.ModelForm):
    """Document version upload form"""
    
    class Meta:
        model = Document
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'
            })
        }
    
    change_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe what changes were made...'
        })
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('File size cannot exceed 10MB.')
        return file


class DocumentTemplateForm(forms.ModelForm):
    """Document template form"""
    
    class Meta:
        model = DocumentTemplate
        fields = ['name', 'template_type', 'description', 'template_content', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'template_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'template_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Enter template content in JSON format'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_template_content(self):
        template_content = self.cleaned_data.get('template_content')
        
        if template_content:
            try:
                import json
                if isinstance(template_content, str):
                    json.loads(template_content)
            except json.JSONDecodeError:
                raise ValidationError('Template content must be valid JSON.')
        
        return template_content
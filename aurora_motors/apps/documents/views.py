from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
import mimetypes
import os

from .models import (
    Document, DocumentCategory, DocumentShare, DocumentAuditLog,
    DocumentVersion, DocumentTemplate
)
from .forms import (
    DocumentUploadForm, DocumentUpdateForm, DocumentReviewForm,
    DocumentShareForm, DocumentCategoryForm, DocumentSearchForm,
    BulkDocumentActionForm, DocumentVersionUploadForm, DocumentTemplateForm
)
from apps.accounts.permissions import StaffRequiredMixin, CustomerRequiredMixin


class DocumentListView(LoginRequiredMixin, ListView):
    """Document list view"""
    
    model = Document
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Document.objects.select_related(
            'category', 'user', 'verified_by'
        ).order_by('-created_at')
        
        # Staff can see all documents, customers only their own
        if not (self.request.user.is_staff_member or self.request.user.is_admin_user):
            queryset = queryset.filter(user=self.request.user)
        
        # Apply search filters
        self.search_form = DocumentSearchForm(self.request.GET)
        if self.search_form.is_valid():
            search = self.search_form.cleaned_data.get('search')
            document_type = self.search_form.cleaned_data.get('document_type')
            category = self.search_form.cleaned_data.get('category')
            status = self.search_form.cleaned_data.get('status')
            date_from = self.search_form.cleaned_data.get('date_from')
            date_to = self.search_form.cleaned_data.get('date_to')
            expiring_soon = self.search_form.cleaned_data.get('expiring_soon')
            
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search) |
                    Q(document_number__icontains=search) |
                    Q(issuing_authority__icontains=search)
                )
            
            if document_type:
                queryset = queryset.filter(document_type=document_type)
            
            if category:
                queryset = queryset.filter(category=category)
            
            if status:
                queryset = queryset.filter(status=status)
            
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
            
            if expiring_soon:
                future_date = timezone.now().date() + timezone.timedelta(days=30)
                queryset = queryset.filter(
                    expiry_date__lte=future_date,
                    expiry_date__gte=timezone.now().date()
                )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = getattr(self, 'search_form', DocumentSearchForm())
        
        # Add statistics for staff
        if self.request.user.is_staff_member or self.request.user.is_admin_user:
            context['stats'] = {
                'total': Document.objects.count(),
                'pending': Document.objects.filter(status='pending').count(),
                'approved': Document.objects.filter(status='approved').count(),
                'rejected': Document.objects.filter(status='rejected').count(),
                'expired': Document.objects.filter(status='expired').count(),
            }
        
        # Add user-specific stats
        user_docs = Document.objects.filter(user=self.request.user)
        context['user_stats'] = {
            'total': user_docs.count(),
            'approved': user_docs.filter(status='approved').count(),
            'pending': user_docs.filter(status='pending').count(),
            'expiring_soon': user_docs.filter(
                expiry_date__lte=timezone.now().date() + timezone.timedelta(days=30),
                expiry_date__gte=timezone.now().date()
            ).count(),
        }
        
        return context


class DocumentDetailView(LoginRequiredMixin, DetailView):
    """Document detail view"""
    
    model = Document
    template_name = 'documents/document_detail.html'
    context_object_name = 'document'
    
    def get_queryset(self):
        queryset = Document.objects.select_related(
            'category', 'user', 'verified_by'
        ).prefetch_related('versions', 'shares', 'audit_logs')
        
        # Staff can see all documents, customers only their own or shared
        if self.request.user.is_staff_member or self.request.user.is_admin_user:
            return queryset
        else:
            return queryset.filter(
                Q(user=self.request.user) |
                Q(shares__shared_with=self.request.user, shares__is_active=True)
            )
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        
        # Log document view
        DocumentAuditLog.objects.create(
            document=self.object,
            user=request.user,
            action='viewed',
            description=f"Document viewed by {request.user.get_full_name()}",
            ip_address=self.get_client_ip()
        )
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.object
        
        # Check permissions
        context['can_edit'] = (
            document.user == self.request.user or
            self.request.user.is_staff_member or
            self.request.user.is_admin_user
        )
        
        context['can_review'] = (
            self.request.user.is_staff_member or
            self.request.user.is_admin_user
        ) and document.status == 'pending'
        
        context['can_download'] = (
            document.user == self.request.user or
            self.request.user.is_staff_member or
            self.request.user.is_admin_user or
            document.shares.filter(
                shared_with=self.request.user,
                is_active=True,
                access_type__in=['view', 'download']
            ).exists()
        )
        
        # Add forms
        if context['can_review']:
            context['review_form'] = DocumentReviewForm()
        
        if context['can_edit']:
            context['share_form'] = DocumentShareForm(user=self.request.user)
            context['version_form'] = DocumentVersionUploadForm()
        
        return context
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class DocumentUploadView(LoginRequiredMixin, CreateView):
    """Document upload view"""
    
    model = Document
    form_class = DocumentUploadForm
    template_name = 'documents/document_upload.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        # Log document upload
        DocumentAuditLog.objects.create(
            document=self.object,
            user=self.request.user,
            action='uploaded',
            description=f"Document uploaded by {self.request.user.get_full_name()}",
            ip_address=self.get_client_ip()
        )
        
        messages.success(
            self.request,
            'Document uploaded successfully! It will be reviewed by our staff.'
        )
        return response
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class DocumentUpdateView(LoginRequiredMixin, UpdateView):
    """Document update view"""
    
    model = Document
    form_class = DocumentUpdateForm
    template_name = 'documents/document_update.html'
    
    def get_queryset(self):
        # Users can only edit their own documents
        if self.request.user.is_staff_member or self.request.user.is_admin_user:
            return Document.objects.all()
        return Document.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log document update
        DocumentAuditLog.objects.create(
            document=self.object,
            user=self.request.user,
            action='updated',
            description=f"Document updated by {self.request.user.get_full_name()}",
            ip_address=self.get_client_ip()
        )
        
        messages.success(self.request, 'Document updated successfully!')
        return response
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    """Document delete view"""
    
    model = Document
    template_name = 'documents/document_confirm_delete.html'
    success_url = reverse_lazy('documents:list')
    
    def get_queryset(self):
        # Users can only delete their own documents
        if self.request.user.is_staff_member or self.request.user.is_admin_user:
            return Document.objects.all()
        return Document.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        document = self.get_object()
        
        # Log document deletion
        DocumentAuditLog.objects.create(
            document=document,
            user=request.user,
            action='deleted',
            description=f"Document deleted by {request.user.get_full_name()}",
            ip_address=self.get_client_ip()
        )
        
        messages.success(request, 'Document deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


@login_required
def download_document(request, pk):
    """Download document file"""
    
    document = get_object_or_404(Document, pk=pk)
    
    # Check permissions
    can_download = (
        document.user == request.user or
        request.user.is_staff_member or
        request.user.is_admin_user or
        document.shares.filter(
            shared_with=request.user,
            is_active=True,
            access_type__in=['view', 'download']
        ).exists()
    )
    
    if not can_download:
        raise PermissionDenied("You don't have permission to download this document.")
    
    # Check if shared access allows download
    if document.user != request.user and not (request.user.is_staff_member or request.user.is_admin_user):
        share = document.shares.filter(shared_with=request.user, is_active=True).first()
        if share:
            if share.access_type == 'view':
                raise PermissionDenied("You only have view access to this document.")
            # Record access
            share.record_access()
    
    # Log download
    DocumentAuditLog.objects.create(
        document=document,
        user=request.user,
        action='downloaded',
        description=f"Document downloaded by {request.user.get_full_name()}",
        ip_address=get_client_ip(request)
    )
    
    # Serve file
    if document.file:
        response = HttpResponse(
            document.file.read(),
            content_type=mimetypes.guess_type(document.file.name)[0] or 'application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{document.original_filename or document.file.name}"'
        return response
    
    messages.error(request, 'Document file not found.')
    return redirect('documents:detail', pk=document.pk)


@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def review_document(request, pk):
    """Review document (staff only)"""
    
    document = get_object_or_404(Document, pk=pk)
    
    if document.status != 'pending':
        messages.error(request, 'This document has already been reviewed.')
        return redirect('documents:detail', pk=document.pk)
    
    if request.method == 'POST':
        form = DocumentReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            notes = form.cleaned_data['review_notes']
            
            if action == 'approve':
                document.approve(request.user, notes)
                messages.success(request, 'Document approved successfully!')
            elif action == 'reject':
                rejection_reason = form.cleaned_data['rejection_reason']
                document.reject(request.user, rejection_reason, notes)
                messages.success(request, 'Document rejected.')
            
            # Log the review
            DocumentAuditLog.objects.create(
                document=document,
                user=request.user,
                action=action + 'd',
                description=f"Document {action}d by {request.user.get_full_name()}",
                ip_address=get_client_ip(request)
            )
            
            return redirect('documents:detail', pk=document.pk)
    
    return redirect('documents:detail', pk=document.pk)


@login_required
def share_document(request, pk):
    """Share document with another user"""
    
    document = get_object_or_404(Document, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = DocumentShareForm(request.POST, user=request.user)
        if form.is_valid():
            share = form.save(commit=False)
            share.document = document
            share.shared_by = request.user
            share.save()
            
            # Log the sharing
            DocumentAuditLog.objects.create(
                document=document,
                user=request.user,
                action='shared',
                description=f"Document shared with {share.shared_with.get_full_name()}",
                ip_address=get_client_ip(request)
            )
            
            messages.success(
                request,
                f'Document shared with {share.shared_with.get_full_name()} successfully!'
            )
            return redirect('documents:detail', pk=document.pk)
    
    return redirect('documents:detail', pk=document.pk)


@login_required
def upload_document_version(request, pk):
    """Upload new version of document"""
    
    document = get_object_or_404(Document, pk=pk)
    
    # Check permissions
    if not (document.user == request.user or request.user.is_staff_member or request.user.is_admin_user):
        raise PermissionDenied("You don't have permission to update this document.")
    
    if request.method == 'POST':
        form = DocumentVersionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Create new version
            version_number = document.versions.count() + 1
            
            DocumentVersion.objects.create(
                document=document,
                version_number=version_number,
                file=form.cleaned_data['file'],
                uploaded_by=request.user,
                change_notes=form.cleaned_data['change_notes']
            )
            
            # Update main document file
            document.file = form.cleaned_data['file']
            document.status = 'pending'  # Reset to pending for review
            document.save()
            
            # Log version upload
            DocumentAuditLog.objects.create(
                document=document,
                user=request.user,
                action='updated',
                description=f"New version (v{version_number}) uploaded by {request.user.get_full_name()}",
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, f'Document version {version_number} uploaded successfully!')
            return redirect('documents:detail', pk=document.pk)
    
    return redirect('documents:detail', pk=document.pk)


class DocumentCategoryListView(StaffRequiredMixin, ListView):
    """Document category list view"""
    
    model = DocumentCategory
    template_name = 'documents/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return DocumentCategory.objects.annotate(
            document_count=Count('documents')
        ).order_by('sort_order', 'name')


class DocumentCategoryCreateView(StaffRequiredMixin, CreateView):
    """Create document category"""
    
    model = DocumentCategory
    form_class = DocumentCategoryForm
    template_name = 'documents/category_form.html'
    success_url = reverse_lazy('documents:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Document category created successfully!')
        return super().form_valid(form)


class DocumentCategoryUpdateView(StaffRequiredMixin, UpdateView):
    """Update document category"""
    
    model = DocumentCategory
    form_class = DocumentCategoryForm
    template_name = 'documents/category_form.html'
    success_url = reverse_lazy('documents:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Document category updated successfully!')
        return super().form_valid(form)


@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def bulk_document_actions(request):
    """Bulk actions on documents"""
    
    if request.method == 'POST':
        queryset = Document.objects.filter(status='pending')
        form = BulkDocumentActionForm(request.POST, queryset=queryset)
        
        if form.is_valid():
            action = form.cleaned_data['action']
            documents = form.cleaned_data['documents']
            notes = form.cleaned_data['notes']
            
            updated_count = 0
            
            for document in documents:
                if action == 'approve':
                    document.approve(request.user, notes)
                elif action == 'reject':
                    document.reject(request.user, 'Bulk rejection', notes)
                elif action == 'delete':
                    document.delete()
                
                updated_count += 1
            
            messages.success(
                request,
                f'{updated_count} documents processed successfully!'
            )
            return redirect('documents:list')
    else:
        queryset = Document.objects.filter(status='pending')
        form = BulkDocumentActionForm(queryset=queryset)
    
    return render(request, 'documents/bulk_actions.html', {
        'form': form
    })


# AJAX Views
@require_http_methods(["GET"])
@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def document_statistics(request):
    """Get document statistics"""
    
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timezone.timedelta(days=days)
    
    documents = Document.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    stats = {
        'total_documents': documents.count(),
        'pending_review': documents.filter(status='pending').count(),
        'approved_documents': documents.filter(status='approved').count(),
        'rejected_documents': documents.filter(status='rejected').count(),
        'expired_documents': documents.filter(status='expired').count(),
        'by_type': {},
        'expiring_soon': 0,
        'upload_trend': [],
    }
    
    # Documents by type
    type_data = documents.values('document_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    for item in type_data:
        stats['by_type'][item['document_type']] = item['count']
    
    # Documents expiring soon
    future_date = timezone.now().date() + timezone.timedelta(days=30)
    stats['expiring_soon'] = Document.objects.filter(
        expiry_date__lte=future_date,
        expiry_date__gte=timezone.now().date(),
        status='approved'
    ).count()
    
    # Daily upload trend
    from django.db.models.functions import TruncDate
    daily_data = documents.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    for item in daily_data:
        stats['upload_trend'].append({
            'date': item['date'].isoformat(),
            'count': item['count']
        })
    
    return JsonResponse(stats)


@require_http_methods(["POST"])
@login_required
def check_document_requirements(request):
    """Check document requirements for user"""
    
    user = request.user
    required_categories = DocumentCategory.objects.filter(is_required=True, is_active=True)
    
    missing_documents = []
    expiring_documents = []
    
    for category in required_categories:
        # Check if user has approved document in this category
        user_docs = Document.objects.filter(
            user=user,
            category=category,
            status='approved'
        )
        
        if not user_docs.exists():
            missing_documents.append({
                'category': category.name,
                'description': category.description
            })
        else:
            # Check for expiring documents
            future_date = timezone.now().date() + timezone.timedelta(days=30)
            expiring = user_docs.filter(
                expiry_date__lte=future_date,
                expiry_date__gte=timezone.now().date()
            )
            
            for doc in expiring:
                expiring_documents.append({
                    'name': doc.name,
                    'expiry_date': doc.expiry_date.isoformat(),
                    'days_until_expiry': doc.days_until_expiry
                })
    
    return JsonResponse({
        'missing_documents': missing_documents,
        'expiring_documents': expiring_documents,
        'requirements_met': len(missing_documents) == 0
    })


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Dashboard view
class DocumentDashboardView(StaffRequiredMixin, ListView):
    """Document management dashboard"""
    
    model = Document
    template_name = 'documents/dashboard.html'
    context_object_name = 'recent_documents'
    
    def get_queryset(self):
        return Document.objects.select_related(
            'user', 'category'
        ).order_by('-created_at')[:10]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        today = timezone.now().date()
        
        # Today's statistics
        context['documents_uploaded_today'] = Document.objects.filter(
            created_at__date=today
        ).count()
        
        context['documents_reviewed_today'] = Document.objects.filter(
            verification_date__date=today
        ).count()
        
        # Pending reviews
        context['pending_reviews'] = Document.objects.filter(
            status='pending'
        ).count()
        
        # Documents expiring soon
        future_date = today + timezone.timedelta(days=30)
        context['expiring_soon'] = Document.objects.filter(
            expiry_date__lte=future_date,
            expiry_date__gte=today,
            status='approved'
        ).count()
        
        # Recent activity
        context['recent_audit_logs'] = DocumentAuditLog.objects.select_related(
            'document', 'user'
        ).order_by('-created_at')[:10]
        
        # Document type statistics
        context['document_types'] = Document.objects.values(
            'document_type'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Category usage
        context['category_usage'] = DocumentCategory.objects.annotate(
            usage_count=Count('documents')
        ).filter(is_active=True).order_by('-usage_count')[:5]
        
        return context


# Document Template Views
class DocumentTemplateListView(StaffRequiredMixin, ListView):
    """Document template list view"""
    
    model = DocumentTemplate
    template_name = 'documents/template_list.html'
    context_object_name = 'templates'


class DocumentTemplateCreateView(StaffRequiredMixin, CreateView):
    """Create document template"""
    
    model = DocumentTemplate
    form_class = DocumentTemplateForm
    template_name = 'documents/template_form.html'
    success_url = reverse_lazy('documents:template_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Document template created successfully!')
        return super().form_valid(form)


class DocumentTemplateUpdateView(StaffRequiredMixin, UpdateView):
    """Update document template"""
    
    model = DocumentTemplate
    form_class = DocumentTemplateForm
    template_name = 'documents/template_form.html'
    success_url = reverse_lazy('documents:template_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Document template updated successfully!')
        return super().form_valid(form)


class SharedDocumentsView(LoginRequiredMixin, ListView):
    """View documents shared with user"""
    
    model = DocumentShare
    template_name = 'documents/shared_documents.html'
    context_object_name = 'shared_documents'
    paginate_by = 20
    
    def get_queryset(self):
        return DocumentShare.objects.filter(
            shared_with=self.request.user,
            is_active=True
        ).select_related('document', 'shared_by').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        shares = self.get_queryset()
        context['stats'] = {
            'total_shared': shares.count(),
            'view_only': shares.filter(access_type='view').count(),
            'download_access': shares.filter(access_type='download').count(),
            'expiring_soon': shares.filter(
                expires_at__lte=timezone.now() + timezone.timedelta(days=7)
            ).count(),
        }
        
        return context


# Document validation views
@login_required
def validate_document_upload(request):
    """Validate document before upload (AJAX)"""
    
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        
        file_size = data.get('file_size', 0)
        file_name = data.get('file_name', '')
        category_id = data.get('category_id')
        
        errors = []
        
        # Check file size (10MB limit)
        if file_size > 10 * 1024 * 1024:
            errors.append('File size cannot exceed 10MB.')
        
        # Check file extension
        if file_name:
            file_extension = os.path.splitext(file_name)[1][1:].lower()
            allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']
            
            if file_extension not in allowed_extensions:
                errors.append(f'File type .{file_extension} is not allowed.')
        
        # Check category restrictions
        if category_id:
            try:
                category = DocumentCategory.objects.get(pk=category_id)
                
                if category.max_file_size and file_size > category.max_file_size:
                    max_size_mb = category.max_file_size / 1024 / 1024
                    errors.append(f'File size exceeds category limit of {max_size_mb:.1f}MB.')
                
                if category.allowed_extensions and file_extension not in category.allowed_extensions:
                    errors.append(f'File type not allowed for this category.')
            
            except DocumentCategory.DoesNotExist:
                errors.append('Invalid category selected.')
        
        return JsonResponse({
            'valid': len(errors) == 0,
            'errors': errors
        })
    
    return JsonResponse({'valid': False, 'errors': ['Invalid request']})
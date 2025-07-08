from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Avg
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
import json
import uuid

from .models import (
    ContractTemplate, Contract, ContractSignature, ContractRevision,
    ContractAuditLog, ContractReminder, ContractAnalytics
)
from .forms import (
    ContractTemplateForm, ContractForm, ContractSignatureForm,
    ContractSearchForm, BulkContractCreateForm, ContractReminderForm,
    ContractRevisionForm
)
from apps.bookings.models import Booking
from apps.accounts.permissions import StaffRequiredMixin, CustomerRequiredMixin
from apps.notifications.tasks import send_contract_for_signature


class ContractTemplateListView(StaffRequiredMixin, ListView):
    """Contract template list view"""
    
    model = ContractTemplate
    template_name = 'contracts/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20
    
    def get_queryset(self):
        return ContractTemplate.objects.annotate(
            contract_count=Count('contracts')
        ).order_by('template_type', 'name')


class ContractTemplateDetailView(StaffRequiredMixin, DetailView):
    """Contract template detail view"""
    
    model = ContractTemplate
    template_name = 'contracts/template_detail.html'
    context_object_name = 'template'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template = self.object
        
        # Get recent contracts using this template
        context['recent_contracts'] = Contract.objects.filter(
            template=template
        ).select_related('user', 'booking')[:10]
        
        # Get template statistics
        contracts = Contract.objects.filter(template=template)
        context['stats'] = {
            'total_contracts': contracts.count(),
            'signed_contracts': contracts.filter(status='signed').count(),
            'pending_contracts': contracts.filter(status__in=['draft', 'sent']).count(),
            'expired_contracts': contracts.filter(status='expired').count(),
        }
        
        return context


class ContractTemplateCreateView(StaffRequiredMixin, CreateView):
    """Create contract template"""
    
    model = ContractTemplate
    form_class = ContractTemplateForm
    template_name = 'contracts/template_form.html'
    success_url = reverse_lazy('contracts:template_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Contract template created successfully!')
        return super().form_valid(form)


class ContractTemplateUpdateView(StaffRequiredMixin, UpdateView):
    """Update contract template"""
    
    model = ContractTemplate
    form_class = ContractTemplateForm
    template_name = 'contracts/template_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Contract template updated successfully!')
        return super().form_valid(form)


class ContractListView(LoginRequiredMixin, ListView):
    """Contract list view"""
    
    model = Contract
    template_name = 'contracts/contract_list.html'
    context_object_name = 'contracts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Contract.objects.select_related(
            'template', 'user', 'booking'
        ).order_by('-created_at')
        
        # Staff can see all contracts, customers only their own
        if not (self.request.user.is_staff_member or self.request.user.is_admin_user):
            queryset = queryset.filter(user=self.request.user)
        
        # Apply search filters
        self.search_form = ContractSearchForm(self.request.GET)
        if self.search_form.is_valid():
            search = self.search_form.cleaned_data.get('search')
            status = self.search_form.cleaned_data.get('status')
            template_type = self.search_form.cleaned_data.get('template_type')
            date_from = self.search_form.cleaned_data.get('date_from')
            date_to = self.search_form.cleaned_data.get('date_to')
            
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(user__first_name__icontains=search) |
                    Q(user__last_name__icontains=search) |
                    Q(user__email__icontains=search) |
                    Q(booking__booking_number__icontains=search)
                )
            
            if status:
                queryset = queryset.filter(status=status)
            
            if template_type:
                queryset = queryset.filter(template__template_type=template_type)
            
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = getattr(self, 'search_form', ContractSearchForm())
        
        # Add statistics for staff
        if self.request.user.is_staff_member or self.request.user.is_admin_user:
            context['stats'] = {
                'total': Contract.objects.count(),
                'pending': Contract.objects.filter(status__in=['draft', 'sent']).count(),
                'signed': Contract.objects.filter(status='signed').count(),
                'expired': Contract.objects.filter(status='expired').count(),
            }
        
        return context


class ContractDetailView(LoginRequiredMixin, DetailView):
    """Contract detail view"""
    
    model = Contract
    template_name = 'contracts/contract_detail.html'
    context_object_name = 'contract'
    slug_field = 'contract_id'
    slug_url_kwarg = 'contract_id'
    
    def get_queryset(self):
        queryset = Contract.objects.select_related(
            'template', 'user', 'booking', 'created_by'
        ).prefetch_related('signatures', 'audit_logs', 'revisions')
        
        # Staff can see all contracts, customers only their own
        if self.request.user.is_staff_member or self.request.user.is_admin_user:
            return queryset
        else:
            return queryset.filter(user=self.request.user)
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        
        # Record the view
        contract = self.object
        analytics, created = ContractAnalytics.objects.get_or_create(contract=contract)
        analytics.record_view(request.user)
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.object
        
        # Add signature form if contract can be signed
        if contract.can_be_signed and contract.user == self.request.user:
            context['signature_form'] = ContractSignatureForm()
        
        # Add forms for staff
        if self.request.user.is_staff_member or self.request.user.is_admin_user:
            context['reminder_form'] = ContractReminderForm()
            context['revision_form'] = ContractRevisionForm(
                initial={'content': contract.content}
            )
        
        # Check permissions
        context['can_sign'] = (
            contract.can_be_signed and 
            contract.user == self.request.user
        )
        context['can_manage'] = (
            self.request.user.is_staff_member or 
            self.request.user.is_admin_user
        )
        
        return context


class ContractCreateView(StaffRequiredMixin, CreateView):
    """Create contract from booking"""
    
    model = Contract
    form_class = ContractForm
    template_name = 'contracts/contract_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs['booking_pk'])
        self.template = get_object_or_404(ContractTemplate, pk=kwargs['template_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Generate contract content from template
        context = {
            'customer_name': self.booking.user.get_full_name(),
            'customer_email': self.booking.user.email,
            'booking_number': self.booking.booking_number,
            'vehicle_name': str(self.booking.vehicle),
            'start_date': self.booking.start_date.strftime('%Y-%m-%d'),
            'end_date': self.booking.end_date.strftime('%Y-%m-%d'),
            'total_amount': self.booking.total_amount,
            'current_date': timezone.now().strftime('%Y-%m-%d'),
        }
        
        initial['title'] = f"{self.template.name} - {self.booking.booking_number}"
        initial['content'] = self.template.render_content(context)
        
        return initial
    
    def form_valid(self, form):
        form.instance.template = self.template
        form.instance.booking = self.booking
        form.instance.user = self.booking.user
        form.instance.created_by = self.request.user
        
        # Set expiry date
        expires_in_days = form.cleaned_data.get('expires_in_days', 7)
        form.instance.expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
        
        response = super().form_valid(form)
        
        # Generate PDF
        self.object.generate_pdf()
        
        # Create analytics record
        ContractAnalytics.objects.create(contract=self.object)
        
        # Log creation
        ContractAuditLog.objects.create(
            contract=self.object,
            user=self.request.user,
            action='created',
            description=f"Contract created by {self.request.user.get_full_name()}"
        )
        
        messages.success(self.request, 'Contract created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking'] = self.booking
        context['template'] = self.template
        return context


@login_required
def contract_sign_view(request, contract_id):
    """Contract signing view"""
    
    try:
        contract_uuid = uuid.UUID(contract_id)
        contract = get_object_or_404(
            Contract,
            contract_id=contract_uuid,
            user=request.user
        )
    except ValueError:
        raise Http404("Invalid contract ID")
    
    # Check if contract can be signed
    if not contract.can_be_signed:
        messages.error(request, 'This contract cannot be signed.')
        return redirect('contracts:detail', contract_id=contract.contract_id)
    
    if request.method == 'POST':
        form = ContractSignatureForm(request.POST, request.FILES)
        if form.is_valid():
            # Prepare signature data
            signature_method = form.cleaned_data['signature_method']
            signature_data = {}
            
            if signature_method == 'draw':
                signature_data = {
                    'method': 'draw',
                    'data': form.cleaned_data['signature_data']
                }
            elif signature_method == 'type':
                signature_data = {
                    'method': 'type',
                    'text': form.cleaned_data['typed_signature']
                }
            elif signature_method == 'upload':
                # Handle file upload
                signature_file = form.cleaned_data['signature_file']
                # Save file and store path
                signature_data = {
                    'method': 'upload',
                    'filename': signature_file.name
                }
            
            # Get client info
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Sign the contract
            contract.sign_contract(signature_data, ip_address, user_agent)
            
            # Create signature record
            ContractSignature.objects.create(
                contract=contract,
                signer=request.user,
                signature_type='customer',
                signature_data=signature_data,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Log the signing
            ContractAuditLog.objects.create(
                contract=contract,
                user=request.user,
                action='signed',
                description=f"Contract signed by {request.user.get_full_name()}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Update analytics
            if hasattr(contract, 'analytics'):
                contract.analytics.record_signed()
            
            messages.success(
                request,
                'Contract signed successfully! You will receive a confirmation email.'
            )
            return redirect('contracts:detail', contract_id=contract.contract_id)
    else:
        form = ContractSignatureForm()
    
    # Record sign attempt
    if hasattr(contract, 'analytics'):
        contract.analytics.record_sign_attempt()
    
    return render(request, 'contracts/contract_sign.html', {
        'contract': contract,
        'form': form
    })


@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def send_contract_for_signature(request, contract_id):
    """Send contract for signature"""
    
    try:
        contract_uuid = uuid.UUID(contract_id)
        contract = get_object_or_404(Contract, contract_id=contract_uuid)
    except ValueError:
        raise Http404("Invalid contract ID")
    
    if contract.status != 'draft':
        messages.error(request, 'Only draft contracts can be sent for signature.')
        return redirect('contracts:detail', contract_id=contract.contract_id)
    
    # Send for signature
    contract.send_for_signature()
    
    # Log the action
    ContractAuditLog.objects.create(
        contract=contract,
        user=request.user,
        action='sent',
        description=f"Contract sent for signature by {request.user.get_full_name()}"
    )
    
    messages.success(request, 'Contract sent for signature successfully!')
    return redirect('contracts:detail', contract_id=contract.contract_id)


@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def cancel_contract(request, contract_id):
    """Cancel contract"""
    
    try:
        contract_uuid = uuid.UUID(contract_id)
        contract = get_object_or_404(Contract, contract_id=contract_uuid)
    except ValueError:
        raise Http404("Invalid contract ID")
    
    if contract.status in ['signed', 'completed']:
        messages.error(request, 'Signed or completed contracts cannot be cancelled.')
        return redirect('contracts:detail', contract_id=contract.contract_id)
    
    if request.method == 'POST':
        contract.status = 'cancelled'
        contract.save()
        
        # Log the cancellation
        ContractAuditLog.objects.create(
            contract=contract,
            user=request.user,
            action='cancelled',
            description=f"Contract cancelled by {request.user.get_full_name()}"
        )
        
        messages.success(request, 'Contract cancelled successfully!')
        return redirect('contracts:detail', contract_id=contract.contract_id)
    
    return render(request, 'contracts/contract_cancel.html', {
        'contract': contract
    })


@login_required
def download_contract_pdf(request, contract_id, signed=False):
    """Download contract PDF"""
    
    try:
        contract_uuid = uuid.UUID(contract_id)
        contract = get_object_or_404(Contract, contract_id=contract_uuid)
    except ValueError:
        raise Http404("Invalid contract ID")
    
    # Check permissions
    if not (contract.user == request.user or request.user.is_staff_member or request.user.is_admin_user):
        messages.error(request, 'You do not have permission to download this contract.')
        return redirect('contracts:detail', contract_id=contract.contract_id)
    
    # Determine which PDF to serve
    pdf_file = contract.signed_pdf_file if signed and contract.signed_pdf_file else contract.pdf_file
    
    if not pdf_file:
        # Generate PDF if it doesn't exist
        if signed and contract.status == 'signed':
            contract.generate_signed_pdf()
            pdf_file = contract.signed_pdf_file
        else:
            contract.generate_pdf()
            pdf_file = contract.pdf_file
    
    if pdf_file:
        # Update analytics
        if hasattr(contract, 'analytics'):
            contract.analytics.record_download(request.user)
        
        # Serve the file
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        filename = f"contract_{contract.contract_id}{'_signed' if signed else ''}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    messages.error(request, 'PDF file not available.')
    return redirect('contracts:detail', contract_id=contract.contract_id)


@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def bulk_create_contracts(request):
    """Bulk create contracts for multiple bookings"""
    
    if request.method == 'POST':
        # Get bookings that need contracts
        bookings_queryset = Booking.objects.filter(
            status__in=['confirmed', 'active']
        ).exclude(
            contracts__isnull=False
        ).select_related('user', 'vehicle')
        
        form = BulkContractCreateForm(request.POST, bookings_queryset=bookings_queryset)
        
        if form.is_valid():
            template = form.cleaned_data['template']
            bookings = form.cleaned_data['bookings']
            expires_in_days = form.cleaned_data['expires_in_days']
            send_immediately = form.cleaned_data['send_immediately']
            
            created_contracts = []
            
            for booking in bookings:
                # Create contract
                contract = template.create_contract(
                    booking=booking,
                    user=booking.user,
                    context={
                        'customer_name': booking.user.get_full_name(),
                        'customer_email': booking.user.email,
                        'booking_number': booking.booking_number,
                        'vehicle_name': str(booking.vehicle),
                        'start_date': booking.start_date.strftime('%Y-%m-%d'),
                        'end_date': booking.end_date.strftime('%Y-%m-%d'),
                        'total_amount': booking.total_amount,
                        'current_date': timezone.now().strftime('%Y-%m-%d'),
                    }
                )
                
                contract.created_by = request.user
                contract.expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
                contract.save()
                
                # Generate PDF
                contract.generate_pdf()
                
                # Create analytics
                ContractAnalytics.objects.create(contract=contract)
                
                # Send for signature if requested
                if send_immediately:
                    contract.send_for_signature()
                
                created_contracts.append(contract)
            
            messages.success(
                request,
                f'{len(created_contracts)} contracts created successfully!'
            )
            return redirect('contracts:list')
    else:
        bookings_queryset = Booking.objects.filter(
            status__in=['confirmed', 'active']
        ).exclude(
            contracts__isnull=False
        ).select_related('user', 'vehicle')
        
        form = BulkContractCreateForm(bookings_queryset=bookings_queryset)
    
    return render(request, 'contracts/bulk_create.html', {
        'form': form
    })


# AJAX Views
@require_http_methods(["GET"])
@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def contract_statistics(request):
    """Get contract statistics"""
    
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timezone.timedelta(days=days)
    
    contracts = Contract.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    stats = {
        'total_contracts': contracts.count(),
        'signed_contracts': contracts.filter(status='signed').count(),
        'pending_contracts': contracts.filter(status__in=['draft', 'sent']).count(),
        'expired_contracts': contracts.filter(status='expired').count(),
        'by_template': {},
        'signing_rate': 0,
        'average_signing_time': 0,
    }
    
    # Contracts by template
    template_data = contracts.values(
        'template__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    for item in template_data:
        stats['by_template'][item['template__name']] = item['count']
    
    # Calculate signing rate
    total_sent = contracts.filter(status__in=['sent', 'signed', 'expired']).count()
    if total_sent > 0:
        signed_count = contracts.filter(status='signed').count()
        stats['signing_rate'] = round((signed_count / total_sent) * 100, 1)
    
    # Calculate average signing time
    signed_contracts = contracts.filter(
        status='signed',
        sent_date__isnull=False,
        signed_date__isnull=False
    )
    
    if signed_contracts.exists():
        total_time = sum([
            (contract.signed_date - contract.sent_date).total_seconds()
            for contract in signed_contracts
        ])
        average_seconds = total_time / signed_contracts.count()
        stats['average_signing_time'] = round(average_seconds / 3600, 1)  # Convert to hours
    
    return JsonResponse(stats)


@require_http_methods(["POST"])
@user_passes_test(lambda u: u.is_staff_member or u.is_admin_user)
def create_contract_reminder(request, contract_id):
    """Create contract reminder"""
    
    try:
        contract_uuid = uuid.UUID(contract_id)
        contract = get_object_or_404(Contract, contract_id=contract_uuid)
    except ValueError:
        return JsonResponse({'error': 'Invalid contract ID'}, status=400)
    
    form = ContractReminderForm(request.POST)
    if form.is_valid():
        reminder = ContractReminder.objects.create(
            contract=contract,
            reminder_date=form.cleaned_data['reminder_date'],
            subject=form.cleaned_data['subject'],
            message=form.cleaned_data['message']
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Reminder created successfully'
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Dashboard view
class ContractDashboardView(StaffRequiredMixin, TemplateView):
    """Contract management dashboard"""
    
    template_name = 'contracts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        today = timezone.now().date()
        
        # Today's statistics
        context['contracts_created_today'] = Contract.objects.filter(
            created_at__date=today
        ).count()
        
        context['contracts_signed_today'] = Contract.objects.filter(
            signed_date__date=today
        ).count()
        
        context['contracts_expiring_soon'] = Contract.objects.filter(
            status='sent',
            expires_at__date__lte=today + timezone.timedelta(days=3)
        ).count()
        
        # Recent activity
        context['recent_contracts'] = Contract.objects.select_related(
            'user', 'booking', 'template'
        ).order_by('-created_at')[:10]
        
        # Pending signatures
        context['pending_signatures'] = Contract.objects.filter(
            status='sent'
        ).select_related('user', 'booking')[:10]
        
        # Template usage statistics
        context['template_usage'] = ContractTemplate.objects.annotate(
            usage_count=Count('contracts')
        ).filter(is_active=True).order_by('-usage_count')[:5]
        
        return context
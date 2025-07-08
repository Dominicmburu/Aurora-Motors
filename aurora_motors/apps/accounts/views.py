from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    CreateView, UpdateView, DetailView, ListView, TemplateView
)
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.views import LoginView as BaseLoginView

from .models import CustomUser, UserProfile, UserActivity
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm,
    ExtendedProfileForm, PasswordChangeForm
)
from apps.bookings.models import Booking
from apps.documents.models import Document


class RegisterView(CreateView):
    """User registration view"""
    
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Create user profile
        UserProfile.objects.create(user=self.object)
        
        # Log activity
        UserActivity.objects.create(
            user=self.object,
            activity_type='registration',
            description='User registered',
            ip_address=self.get_client_ip()
        )
        
        messages.success(
            self.request,
            'Registration successful! Please log in to continue.'
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


class LoginView(BaseLoginView):
    """Custom login view"""
    
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Update last login IP
        user = form.get_user()
        user.last_login_ip = self.get_client_ip()
        user.save(update_fields=['last_login_ip'])
        
        # Log activity
        UserActivity.objects.create(
            user=user,
            activity_type='login',
            description='User logged in',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        messages.success(self.request, f'Welcome back, {user.get_full_name()}!')
        return response
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class DashboardView(LoginRequiredMixin, TemplateView):
    """User dashboard view"""
    
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get recent bookings
        recent_bookings = Booking.objects.filter(
            user=user
        ).order_by('-created_at')[:5]
        
        # Get booking statistics
        booking_stats = {
            'total_bookings': Booking.objects.filter(user=user).count(),
            'active_bookings': Booking.objects.filter(
                user=user, 
                status='confirmed',
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            ).count(),
            'upcoming_bookings': Booking.objects.filter(
                user=user, 
                status='confirmed',
                start_date__gt=timezone.now()
            ).count(),
            'past_bookings': Booking.objects.filter(
                user=user, 
                status='completed'
            ).count(),
        }
        
        # Get recent documents
        recent_documents = Document.objects.filter(
            user=user
        ).order_by('-created_at')[:5]
        
        # Get recent activities
        recent_activities = UserActivity.objects.filter(
            user=user
        ).order_by('-created_at')[:10]
        
        context.update({
            'recent_bookings': recent_bookings,
            'booking_stats': booking_stats,
            'recent_documents': recent_documents,
            'recent_activities': recent_activities,
        })
        
        return context


class ProfileView(LoginRequiredMixin, DetailView):
    """User profile view"""
    
    model = CustomUser
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self):
        return self.request.user


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """User profile update view"""
    
    model = CustomUser
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get or create extended profile
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        
        context['extended_form'] = ExtendedProfileForm(
            instance=profile,
            data=self.request.POST if self.request.method == 'POST' else None
        )
        
        return context
    
    def form_valid(self, form):
        # Save main profile
        response = super().form_valid(form)
        
        # Save extended profile
        extended_form = ExtendedProfileForm(
            self.request.POST, 
            instance=self.request.user.profile
        )
        
        if extended_form.is_valid():
            extended_form.save()
            
            # Check if profile is now complete
            self.check_profile_completion()
            
            # Log activity
            UserActivity.objects.create(
                user=self.request.user,
                activity_type='profile_update',
                description='Profile updated',
                ip_address=self.get_client_ip()
            )
            
            messages.success(self.request, 'Profile updated successfully!')
        else:
            messages.error(self.request, 'Please correct the errors below.')
        
        return response
    
    def check_profile_completion(self):
        """Check if user profile is complete"""
        user = self.request.user
        profile = user.profile
        
        required_fields = [
            user.first_name, user.last_name, user.phone, user.address,
            profile.license_number, profile.license_expiry,
            profile.emergency_contact_name, profile.emergency_contact_phone
        ]
        
        if all(field for field in required_fields):
            user.profile_completed = True
            user.save(update_fields=['profile_completed'])
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


@login_required
def change_password(request):
    """Change user password"""
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log activity
            UserActivity.objects.create(
                user=user,
                activity_type='password_change',
                description='Password changed',
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def logout_view(request):
    """Logout view"""
    
    # Log activity
    UserActivity.objects.create(
        user=request.user,
        activity_type='logout',
        description='User logged out',
        ip_address=get_client_ip(request)
    )
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


class BookingHistoryView(LoginRequiredMixin, ListView):
    """User booking history view"""
    
    model = Booking
    template_name = 'accounts/booking_history.html'
    context_object_name = 'bookings'
    paginate_by = 20
    
    def get_queryset(self):
        return Booking.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class ActivityHistoryView(LoginRequiredMixin, ListView):
    """User activity history view"""
    
    model = UserActivity
    template_name = 'accounts/activity_history.html'
    context_object_name = 'activities'
    paginate_by = 50
    
    def get_queryset(self):
        return UserActivity.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# API Views for AJAX requests
@require_http_methods(["GET"])
@login_required
def check_profile_completion(request):
    """Check if user profile is complete"""
    user = request.user
    
    try:
        profile = user.profile
        required_fields = [
            user.first_name, user.last_name, user.phone, user.address,
            profile.license_number, profile.license_expiry,
            profile.emergency_contact_name, profile.emergency_contact_phone
        ]
        
        completed = all(field for field in required_fields)
        
        return JsonResponse({
            'completed': completed,
            'message': 'Profile is complete' if completed else 'Profile incomplete'
        })
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'completed': False,
            'message': 'Profile not found'
        })


@require_http_methods(["POST"])
@login_required
def update_notification_preferences(request):
    """Update user notification preferences"""
    receive_notifications = request.POST.get('receive_notifications') == 'true'
    receive_marketing = request.POST.get('receive_marketing') == 'true'
    
    user = request.user
    user.receive_notifications = receive_notifications
    user.receive_marketing = receive_marketing
    user.save(update_fields=['receive_notifications', 'receive_marketing'])
    
    return JsonResponse({
        'success': True,
        'message': 'Notification preferences updated'
    })
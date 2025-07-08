from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class CustomerRequiredMixin(UserPassesTestMixin):
    """Mixin to require customer user type"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_customer

class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to require staff user type"""
    
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_staff_member or self.request.user.is_admin_user
        )

class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin user type"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin_user

class VerifiedUserRequiredMixin(UserPassesTestMixin):
    """Mixin to require verified user"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_verified

class ProfileCompleteRequiredMixin(UserPassesTestMixin):
    """Mixin to require complete profile"""
    
    def test_func(self):
        return (self.request.user.is_authenticated and 
                self.request.user.profile_completed)
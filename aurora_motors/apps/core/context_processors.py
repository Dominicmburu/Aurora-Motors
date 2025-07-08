from .models import SiteSettings

def site_settings(request):
    """Add site settings to template context"""
    settings = SiteSettings.get_settings()
    return {
        'site_settings': settings,
        'SITE_NAME': settings.site_name,
        'COMPANY_NAME': settings.company_name,
    }
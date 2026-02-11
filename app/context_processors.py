from datetime import datetime
from django.conf import settings


def current_year(request):
    """Add current year to all template contexts"""
    return {
        'current_year': datetime.now().year
    }


def google_maps(request):
    """Add Google Maps API key to all template contexts"""
    return {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    }

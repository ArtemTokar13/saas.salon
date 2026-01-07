from datetime import datetime


def current_year(request):
    """Add current year to all template contexts"""
    return {
        'current_year': datetime.now().year
    }

from datetime import datetime


def current_year(request):
    """Add current year to all template contexts"""
    return {
        'current_year': datetime.now().year
    }


def unread_notifications(request):
    """Add unread notification count to all template contexts"""
    if request.user.is_authenticated:
        try:
            from notifications.models import Notification
            unread_count = Notification.objects.filter(
                recipient=request.user,
                unread=True
            ).count()
            return {
                'unread_notifications_count': unread_count
            }
        except Exception:
            return {'unread_notifications_count': 0}
    return {'unread_notifications_count': 0}

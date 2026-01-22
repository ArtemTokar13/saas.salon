from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from billing.models import Subscription


def subscription_required(view_func):
    """
    Decorator that checks subscription status:
    - Allows free access for 30 days after admin registration
    - After 30 days, requires active subscription
    - Redirects to subscription details page if subscription is inactive
    - For AJAX requests, returns JSON response instead of redirect
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if not request.user.is_authenticated:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required',
                    'redirect': '/login/'
                }, status=401)
            return redirect('login')
        
        try:
            profile = request.user.userprofile
            
            company = profile.company
            if not company:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'error': 'No company associated with your account.'
                    }, status=403)
                messages.error(request, 'No company associated with your account.')
                return redirect('index')
            
            # Check if within 30-day trial period (based on company's admin registration)
            # Find the admin user for this company to check trial period
            admin_profile = company.userprofile_set.filter(is_admin=True).first()
            if admin_profile:
                trial_end_date = admin_profile.created_at + timedelta(days=30)
                now = timezone.now()
                
                if now < trial_end_date:
                    # Still in trial period - allow access
                    return view_func(request, *args, **kwargs)
            
            # Trial period ended - check for active subscription
            active_subscription = Subscription.objects.filter(
                company=company,
                is_active=True,
                status=Subscription.STATUS_ACTIVE
            ).first()
            
            if active_subscription:
                # Has active subscription - allow access
                return view_func(request, *args, **kwargs)
            
            # No active subscription after trial
            if is_ajax:
                if profile.is_admin:
                    return JsonResponse({
                        'success': False,
                        'error': 'Your trial period has ended. Please subscribe to continue using the service.',
                        'redirect': '/billing/subscription/'
                    }, status=403)
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Your salon does not have an active subscription. Please contact your administrator.',
                        'redirect': '/'
                    }, status=403)
            
            if profile.is_admin:
                # Admin - redirect to subscription page
                messages.warning(
                    request,
                    'Your trial period has ended. Please subscribe to continue using the service.'
                )
                return redirect('subscription_details')
            else:
                # Staff - redirect to home page
                messages.warning(
                    request,
                    'Your salon does not have an active subscription. Please contact your administrator.'
                )
                return redirect('index')
            
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': f'Error checking subscription: {str(e)}'
                }, status=500)
            messages.error(request, f'Error checking subscription: {str(e)}')
            return redirect('index')
    
    return wrapper

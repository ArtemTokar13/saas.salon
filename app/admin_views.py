from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from companies.models import Company, Staff, Service, EmailLog
from bookings.models import Booking, Customer
from billing.models import Plan, Subscription, Transaction
from users.models import UserProfile
from users.models import DailyVisit
import qrcode
from io import BytesIO
import traceback
import logging

logger = logging.getLogger(__name__)


def is_superuser(user):
    return user.is_superuser or user.is_staff


@login_required
@user_passes_test(is_superuser)
def admin_dashboard(request):
    """Super admin dashboard to manage entire platform"""
    
    # Statistics
    total_users = User.objects.count()
    total_companies = Company.objects.count()
    total_bookings = Booking.objects.count()
    total_revenue = Transaction.objects.aggregate(Sum('amount'))['amount__sum'] or 0

    # Visits
    total_visits = DailyVisit.objects.count()
    today_visits = DailyVisit.objects.filter(date=date.today()).count()
    
    # Recent activity
    recent_companies = Company.objects.order_by('-created_at')[:5]
    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_bookings = Booking.objects.select_related('company', 'customer', 'service').order_by('-created_at')[:10]
    recent_transactions = Transaction.objects.select_related('subscription__company', 'subscription__plan').order_by('-transaction_date')[:10]
    
    # Active subscriptions
    active_subscriptions = Subscription.objects.filter(is_active=True).select_related('company', 'plan')
    
    # Plans statistics
    plans = Plan.objects.annotate(
        subscription_count=Count('subscription', filter=Q(subscription__is_active=True))
    )
    
    context = {
        'total_users': total_users,
        'total_companies': total_companies,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'recent_companies': recent_companies,
        'recent_users': recent_users,
        'recent_bookings': recent_bookings,
        'recent_transactions': recent_transactions,
        'active_subscriptions': active_subscriptions,
        'plans': plans,
        'total_visits': total_visits,
        'today_visits': today_visits,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)


@login_required
@user_passes_test(is_superuser)
def manage_users(request):
    """View and manage all users"""
    users = User.objects.select_related('userprofile').order_by('-date_joined')
    
    context = {
        'users': users,
    }
    
    return render(request, 'admin_dashboard/manage_users.html', context)


@login_required
@user_passes_test(is_superuser)
@require_POST
def send_activation_email(request, user_id):
    """Send or resend activation email to a user"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Check if user is already active
        if user.is_active:
            return JsonResponse({'success': False, 'error': 'User is already active.'}, status=400)
        
        # Build activation link (uid + token)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        activate_path = reverse('activate_company', args=[uid, token])
        activate_link = request.build_absolute_uri(activate_path)

        # Send activation email
        subject = 'Activate your account'
        html_message = render_to_string('email/account_activation.html', {
            'activate_link': activate_link,
            'current_year': timezone.now().year,
            'site_name': 'Salon Booking System',
        })
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        recipient_list = [user.email]

        # Create email log entry
        email_log = EmailLog.objects.create(
            recipient_email=user.email,
            subject=subject,
            email_type='account_activation',
            status='pending'
        )

        try:
            msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
            msg.attach_alternative(html_message, "text/html")
            # Send copy to admin and requesting superuser
            bcc_list = ['artemtokartouch@gmail.com']
            if request.user.email:
                bcc_list.append(request.user.email)
            msg.bcc = bcc_list
            msg.send()
            
            email_log.status = 'success'
            email_log.sent_at = timezone.now()
            email_log.save()
            
            return JsonResponse({'success': True, 'message': 'Activation email sent successfully!'})
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()

            email_log.status = 'failed'
            email_log.error_message = error_msg
            email_log.error_traceback = error_trace
            email_log.save()

            logger.error(
                f"Email sending failed for user activation. User: {user.email}, Error: {error_msg}",
                exc_info=True
            )
            
            return JsonResponse({'success': False, 'error': 'Failed to send activation email. Please try again later.'}, status=500)
    except Exception as e:
        logger.error(f"Error in send_activation_email: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@user_passes_test(is_superuser)
def manage_companies(request):
    """View and manage all companies"""
    companies = Company.objects.select_related('administrator').annotate(
        staff_count=Count('staff'),
        service_count=Count('service'),
        booking_count=Count('booking')
    ).order_by('-created_at')
    
    context = {
        'companies': companies,
    }
    
    return render(request, 'admin_dashboard/manage_companies.html', context)


@login_required
@user_passes_test(is_superuser)
def manage_plans(request):
    """View and manage billing plans"""
    plans = Plan.objects.filter(is_active=True).order_by('base_monthly_price')
    
    context = {
        'plans': plans,
    }
    
    return render(request, 'admin_dashboard/manage_plans.html', context)


@login_required
@user_passes_test(is_superuser)
def manage_subscriptions(request):
    """View all subscriptions"""
    subscriptions = Subscription.objects.select_related('company', 'plan').order_by('-start_date')
    
    # Filter options
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        subscriptions = subscriptions.filter(is_active=True)
    elif status_filter == 'inactive':
        subscriptions = subscriptions.filter(is_active=False)
    
    context = {
        'subscriptions': subscriptions,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_dashboard/manage_subscriptions.html', context)


@login_required
@user_passes_test(is_superuser)
def qrcode_generator(request):
    """Generate QR codes from URLs"""
    if request.method == 'POST':
        url = request.POST.get('url', '').strip()
        
        if not url:
            messages.error(request, 'Please provide a URL')
            return render(request, 'admin_dashboard/qrcode_generator.html')
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Create an image with transparent background
        from PIL import Image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to RGBA and make white pixels transparent
        img = img.convert("RGBA")
        datas = img.getdata()
        
        new_data = []
        for item in datas:
            # Change all white (also shades of whites) pixels to transparent
            if item[0] > 200 and item[1] > 200 and item[2] > 200:
                new_data.append((255, 255, 255, 0))  # Transparent
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        
        # Save to BytesIO buffer
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Return as downloadable file
        response = HttpResponse(buffer, content_type='image/png')
        response['Content-Disposition'] = 'attachment; filename="qrcode.png"'
        return response
    
    return render(request, 'admin_dashboard/qrcode_generator.html')

import traceback
from django.shortcuts import render, redirect
from django.core.mail import send_mail, EmailMultiAlternatives
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _
from datetime import datetime
from app.services import send_whatsapp_template
from companies.models import Company, Staff, Service, EmailLog
from app.meta_pixel import send_fb_capi_event
from users.models import UserProfile


def Index(request):
    companies = Company.objects.all()
    # send_whatsapp_template(
    #     to="34674930646",
    #     name="John Doe",
    #     order_id="123456",
    #     date="Jan 17, 2026"
    # )
    return render(request, 'Index.html', {'companies': companies})


def privacy_policy(request):
    return render(request, 'static_pages/privacy_policy.html')


def terms_of_service(request):
    return render(request, 'static_pages/terms_of_service.html')


def cookie_policy(request):
    return render(request, 'static_pages/cookie_policy.html')


def cookie_settings(request):
    return render(request, 'static_pages/cookie_settings.html')


def about_us(request):
    return render(request, 'static_pages/about_us.html')


def how_it_works(request):
    return render(request, 'static_pages/how_it_works.html')


def faq(request):
    return render(request, 'static_pages/faq.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        try:
            full_message = f"From: {name} ({email})\n\n{message}"
            send_mail(
                f"Contact Form: {subject}",
                full_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_EMAIL if hasattr(settings, 'CONTACT_EMAIL') else settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
            messages.success(request, 'Your message has been sent successfully. We will get back to you soon.')
        except Exception as e:
            messages.error(request, 'Failed to send message. Please try again later.')
        
    subject = request.GET.get('subject', '')
    return render(request, 'static_pages/contact.html', {'subject': subject})

#############################################################################
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .services import build_schedule_csv

def schedule_page(request):
    # просто сторінка з формою
    return render(request, "schedule.html")


@csrf_exempt
def generate_schedule(request):
    print(f"Request method: {request.method}")
    print(f"Content type: {request.content_type}")
    print(f"POST data: {dict(request.POST)}")
    print(f"GET data: {dict(request.GET)}")
    print(f"Raw body: {request.body[:500]}")  # First 500 chars
    
    if request.method == "POST":
        # Handle POST request with form data
        payload_str = request.POST.get("payload", "")
        print(f"Payload from POST: '{payload_str}'")
    elif request.method == "GET":
        # Handle direct browser access with query parameters
        payload_str = request.GET.get("payload", "")
        if not payload_str:
            # If no payload provided via GET, redirect to the form page
            return redirect('schedule_page')
    else:
        return HttpResponse("Method not allowed", status=405)
    
    print(f"Final payload_str: '{payload_str}'")
    
    if not payload_str:
        return HttpResponse("Missing payload parameter", status=400)
    
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    try:
        csv_content = build_schedule_csv(payload)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=400)

    response = HttpResponse(csv_content, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="schedule.csv"'
    return response


def registration_thank_you(request):
    """Thank you page after successful registration"""
    if not request.user.is_authenticated:
        return redirect('/')

    user_agent = request.META.get('HTTP_USER_AGENT')
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    send_fb_capi_event(
        user_email=request.user.email,
        user_agent=user_agent,
        user_ip=ip_address,
        event_name='CompleteRegistration'
    )

    company = None
    has_completed_onboarding = False
    try:
        profile = request.user.userprofile
        company = profile.company
        has_completed_onboarding = Service.objects.filter(company=company).exists()
    except Exception:
        pass

    return render(request, 'registration_thank_you.html', {
        'company': company,
        'has_completed_onboarding': has_completed_onboarding,
    })


@login_required
def save_onboarding(request):
    """AJAX endpoint to save onboarding form data (multipart/form-data)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        profile = request.user.userprofile
        company = profile.company
    except Exception:
        return JsonResponse({'error': 'Company not found'}, status=404)

    data = request.POST

    # Company info
    salon_type = data.get('salon_type', '')
    company_name = (data.get('company_name') or '').strip()
    company_address = (data.get('company_address') or '').strip()
    company_city = (data.get('company_city') or '').strip()
    company_phone = (data.get('phone') or '').strip()

    if company_name:
        company.name = company_name
    if company_address:
        company.address = company_address
    if company_city:
        company.city = company_city
    if company_phone:
        company.phone = company_phone
    if salon_type:
        company.salon_type = salon_type or None
    company.save()

    # Service
    service_name = (data.get('service_name') or '').strip()
    service = None
    if service_name:
        try:
            service_duration = max(1, int(data.get('service_duration') or 30))
        except (ValueError, TypeError):
            service_duration = 30
        try:
            service_price = float(data.get('service_price') or 0)
        except (ValueError, TypeError):
            service_price = 0.0
        service = Service.objects.create(
            company=company,
            name=service_name,
            duration=service_duration,
            price=service_price,
        )

    # Staff
    owner_is_staff = data.get('owner_is_staff') == 'true'
    if owner_is_staff:
        staff_name = request.user.get_full_name() or request.user.username
        staff_specialization = ''
    else:
        staff_name = (data.get('staff_name') or '').strip()
        staff_specialization = (data.get('staff_position') or '').strip()

    if staff_name:
        staff = Staff.objects.create(
            company=company,
            name=staff_name,
            specialization=staff_specialization,
            working_days=[0, 1, 2, 3, 4, 5, 6],
        )
        avatar = request.FILES.get('staff_avatar')
        if avatar:
            staff.avatar = avatar
            staff.save()
        if service:
            staff.services.add(service)

    return JsonResponse({'success': True, 'redirect': reverse('booking_calendar')})


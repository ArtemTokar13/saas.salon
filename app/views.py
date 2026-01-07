from django.shortcuts import render
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
from datetime import datetime


def Index(request):
    return render(request, 'Index.html')


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
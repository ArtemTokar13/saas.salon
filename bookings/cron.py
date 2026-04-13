from babel.dates import format_date
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext as _
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from app.services import send_whatsapp_template
from billing.utils import has_whatsapp_feature
from bookings.models import Booking
from companies.models import EmailLog


def send_booking_reminders():
    """
    Send reminders for all bookings scheduled for tomorrow.
    This should be run daily at 14:00.
    """
    now = timezone.localtime(timezone.now())
    tomorrow = now.date() + timedelta(days=1)
    
    # Get all bookings for tomorrow that haven't been reminded yet
    bookings_to_remind = Booking.objects.filter(
        date=tomorrow,
        reminder_sent=False
    ).order_by('start_time')
    
    print(f"Current time: {now}")
    print(f"Sending reminders for bookings on: {tomorrow}")
    print(f"Found {bookings_to_remind.count()} bookings to send reminders for.")

    for booking in bookings_to_remind:
        site_url = getattr(settings, 'SITE_URL')
        booking_link = site_url + reverse('booking_confirmation', args=[booking.id])
        if booking.customer.email:
            subject = _("Reminder: Upcoming Booking for") + " " + booking.service.name
            html_message = render_to_string('email/booking_reminder.html', {
                'company': booking.company,
                'booking': booking,
                'booking_link': booking_link,
                'current_year': timezone.now().year,
            })
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [booking.customer.email]
            email_log = EmailLog.objects.create(
                recipient_email=booking.customer.email,
                subject=subject,
                email_type='booking_reminder',
                status='pending'
            )
            try:
                msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
                msg.attach_alternative(html_message, "text/html")
                msg.send()
                email_log.status = 'sent'
                email_log.sent_at = timezone.now()
                email_log.save()
            except Exception as e:
                email_log.status = 'failed'
                email_log.error_message = str(e)
                email_log.save()

        # Send WhatsApp reminder if company has WhatsApp feature
        if has_whatsapp_feature(booking.company):
            # Use booking_phone if available, otherwise fall back to customer.phone
            phone_to_use = booking.get_phone_for_notifications()
            print(f"Sending WhatsApp reminder to {phone_to_use} for booking {booking.id}")
            res = send_whatsapp_template(
                to=phone_to_use,
                content_sid=settings.TWILIO_REMINDER_TEMPLATE_SID,
                variables={
                    '1': booking.customer.name,
                    '2': booking.company.name,
                    '3': booking.service.name,
                    '4': f'{format_date(booking.date, format="EEEE, d 'de' MMMM", locale='es_ES')}',
                    '5': booking.start_time.strftime("%H:%M"),
                    '6': booking.staff.name,
                    '7': booking_link
                }
            )
            print(f"WhatsApp API response: {res}")
        
        booking.reminder_sent = True
        booking.save()
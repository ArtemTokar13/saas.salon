from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext as _
from django.conf import settings
from django.core.mail import send_mail
from bookings.models import Booking
from companies.models import EmailLog
from app.services import send_whatsapp_template


def send_booking_reminders():
    now = timezone.now()
    reminder_time = now + timedelta(hours=2)  # Remind for bookings in the next two hours
    bookings_to_remind = Booking.objects.filter(start_time__gte=now, start_time__lt=reminder_time, reminder_sent=False)

    for booking in bookings_to_remind:
        if booking.customer.email:
            subject = _("Reminder: Upcoming Booking for") + booking.service.name
            message = _("Dear {}, you have an upcoming booking for {} on {} at {}.").format(
                booking.customer.name,
                booking.service.name,
                booking.date,
                booking.start_time
            )
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [booking.customer.email]
            try:
                send_mail(subject, message, from_email, recipient_list)
            except Exception as e:
                EmailLog.objects.create(
                    company=booking.company,
                    to_email=booking.customer.email,
                    subject=subject,
                    body=message,
                    status='failed',
                    error_message=str(e)
                )

        # TODO: Send reminder via WhatsApp as well
        # res = send_whatsapp_template(
        #     to=booking.customer.phone,
        #     name="jaspers_market_order_confirmation_v1",
        #     date=str(booking.date),
        #     time=str(booking.start_time)
        # )
        # if res.get('error'):
        #     EmailLog.objects.create(
        #         company=booking.company,
        #         to_email=booking.customer.phone,
        #         subject="WhatsApp Reminder Failed",
        #         body=str(res),
        #         status='failed',
        #         error_message=res['error']['message']
        #     )
        
        booking.reminder_sent = True
        booking.save()
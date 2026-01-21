def send_booking_reminders():
    from bookings.models import Booking
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    reminder_time = now + timedelta(hours=1)  # Remind for bookings in the next hour
    bookings_to_remind = Booking.objects.filter(start_time__gte=now, start_time__lt=reminder_time, reminder_sent=False)

    for booking in bookings_to_remind:
        # Send reminder (e.g., via email or SMS)
        # send_reminder(booking)
        booking.reminder_sent = True
        booking.save()
from django.db import models
from django.contrib.auth.models import User
from app.constants import COUNTRY_CHOICES
from companies.models import Company, Staff, Service


BOOCING_CREATED_BY_CHOICES = [
    ('client', 'Client'),
    ('staff', 'Staff'),
    ('whatsapp', 'WhatsApp'),
]


class Customer(models.Model):
    LANGUAGE_CHOICES = [
        ('es', 'Español'),
        ('en', 'English'),
        ('ru', 'Русский'),
        ('uk', 'Українська'),
    ]
    
    name = models.CharField(max_length=255)
    country_code = models.CharField(max_length=10, blank=True, null=True, choices=COUNTRY_CHOICES)
    phone = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
    preferred_language = models.CharField(max_length=5, blank=True, null=True, choices=LANGUAGE_CHOICES, help_text="Customer's preferred language for communications")

    def total_bookings(self):
        return Booking.objects.filter(customer=self, status=1).count()

    def __str__(self):
        return self.name


class Booking(models.Model):
    STATUS = [
        (0, "Pending"),
        (1, "Confirmed"),
        (2, "Cancelled"),
        (3, "PreBooked"),  # Awaiting staff confirmation with price/duration
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)  # Can be NULL until staff confirms
    duration = models.PositiveIntegerField(blank=True, null=True, help_text="Duration in minutes (set by staff if need_staff_confirmation)")
    price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text="Price (set by staff if need_staff_confirmation)")
    status = models.CharField(max_length=20, choices=STATUS, default=0)
    delete_code = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.CharField(max_length=60, blank=True, null=True, choices=BOOCING_CREATED_BY_CHOICES, help_text="Indicates how the booking was created (e.g., 'client', 'staff', 'whatsapp')")
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)  # When staff confirms the booking
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='confirmed_bookings')
    reminder_sent = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    client_notes = models.TextField(blank=True, null=True, help_text="Notes added by the client when booking")
    # Store phone at time of booking to avoid issues when customer phone changes
    booking_phone = models.CharField(max_length=50, blank=True, null=True, help_text="Phone number used when booking was created")
    booking_country_code = models.CharField(max_length=10, blank=True, null=True, choices=COUNTRY_CHOICES, help_text="Country code at time of booking")

    def get_phone_for_notifications(self):
        """Get the phone number to use for notifications (booking_phone or fallback to customer.phone)
        Returns normalized phone number ready for WhatsApp/SMS"""
        from .utils import normalize_phone_number
        
        # Prefer booking_phone (already normalized when saved)
        if self.booking_phone:
            return self.booking_phone
        
        # Fallback to customer phone (normalize it)
        return normalize_phone_number(self.customer.phone)

    def __str__(self):
        return f"{self.customer.name} → {self.service.name} ({self.date})"

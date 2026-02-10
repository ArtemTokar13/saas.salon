from django.db import models
from django.contrib.auth.models import User
from app.constants import COUNTRY_CHOICES
from companies.models import Company, Staff, Service


class Customer(models.Model):
    name = models.CharField(max_length=255)
    country_code = models.CharField(max_length=10, blank=True, null=True, choices=COUNTRY_CHOICES)
    phone = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)

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
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)  # When staff confirms the booking
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='confirmed_bookings')
    reminder_sent = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    client_notes = models.TextField(blank=True, null=True, help_text="Notes added by the client when booking")

    def __str__(self):
        return f"{self.customer.name} → {self.service.name} ({self.date})"

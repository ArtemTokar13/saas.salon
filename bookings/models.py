from django.db import models
from django.contrib.auth.models import User
from companies.models import Company, Staff, Service


class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name


class Booking(models.Model):
    STATUS = [
        (0, "Pending"),
        (1, "Confirmed"),
        (2, "Cancelled"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS, default=0)
    delete_code = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} → {self.service.name} ({self.date})"

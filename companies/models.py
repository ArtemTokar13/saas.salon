from django.db import models
from django.contrib.auth.models import User


DAYS_OF_WEEK = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]

class Company(models.Model):
    administrator = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    map_location = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    social_media = models.JSONField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    logo = models.ImageField(upload_to="uploads/company_logos/", blank=True, null=True)

    def __str__(self):
        return self.name


class Staff(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255, blank=True)
    avatar = models.ImageField(upload_to="uploads/staff_avatars/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Service(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} — {self.salon.name}"


class WorkingHours(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="working_hours")
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_day_off = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.company.name} — {self.get_day_of_week_display()}"
import os
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .utils import company_img_upload
from PIL import Image


DAYS_OF_WEEK = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]


class EmailLog(models.Model):
    """Track email sending attempts and failures for debugging"""
    EMAIL_STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    email_type = models.CharField(max_length=50, default='registration')  # e.g., registration, password_reset
    status = models.CharField(max_length=20, choices=EMAIL_STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    error_traceback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['recipient_email']),
        ]
    
    def __str__(self):
        return f"{self.email_type} - {self.recipient_email} - {self.status}"

class Company(models.Model):
    administrator = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    map_location = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    social_media = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    logo = models.ImageField(upload_to=company_img_upload, blank=True, null=True)
    online_appointments_enabled = models.BooleanField(default=True)
    
    # Stripe Connect fields for receiving payments
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Connect Account ID")
    stripe_onboarding_completed = models.BooleanField(default=False, help_text="Whether Stripe onboarding is complete")
    stripe_charges_enabled = models.BooleanField(default=False, help_text="Whether the account can receive payments")
    stripe_payouts_enabled = models.BooleanField(default=False, help_text="Whether the account can receive payouts")
    stripe_details_submitted = models.BooleanField(default=False, help_text="Whether account details have been submitted")
    accepts_online_payments = models.BooleanField(default=False, help_text="Whether salon accepts online payments for bookings")

    MAX_LOGO_SIZE_KB = 200
    MAX_DIMENSIONS = (400, 400)

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old_logo = Company.objects.get(pk=self.pk).logo
                if old_logo and old_logo != self.logo:
                    if os.path.isfile(old_logo.path):
                        os.remove(old_logo.path)
            except Company.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if self.logo:
            self._optimize_logo()

    def _optimize_logo(self):
        img = Image.open(self.logo.path)
        img.thumbnail(self.MAX_DIMENSIONS, Image.Resampling.LANCZOS)
        quality = 85
        img.save(self.logo.path, optimize=True, quality=quality)

        while os.path.getsize(self.logo.path) > self.MAX_LOGO_SIZE_KB * 1024 and quality > 40:
            quality -= 5
            img.save(self.logo.path, optimize=True, quality=quality)

    def delete(self, *args, **kwargs):
        if self.logo and os.path.isfile(self.logo.path):
            os.remove(self.logo.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class Staff(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    avatar = models.ImageField(upload_to=company_img_upload, blank=True, null=True)
    working_days = models.JSONField(default=list, blank=True)  # List of day numbers (0=Monday, 6=Sunday)
    break_start = models.TimeField(blank=True, null=True)
    break_end = models.TimeField(blank=True, null=True)
    out_of_office = models.BooleanField(default=False)
    out_of_office_start = models.DateField(blank=True, null=True)
    out_of_office_end = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    services = models.ManyToManyField('Service', blank=True, related_name='staff_members')

    MAX_AVATAR_SIZE_KB = 200
    MAX_DIMENSIONS = (400, 400)

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old_avatar = Staff.objects.get(pk=self.pk).avatar
                if old_avatar and old_avatar != self.avatar:
                    if os.path.isfile(old_avatar.path):
                        os.remove(old_avatar.path)
            except Staff.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if self.avatar:
            self._optimize_avatar()

    def _optimize_avatar(self):
        img = Image.open(self.avatar.path)
        img.thumbnail(self.MAX_DIMENSIONS, Image.Resampling.LANCZOS)
        quality = 85
        img.save(self.avatar.path, optimize=True, quality=quality)

        while os.path.getsize(self.avatar.path) > self.MAX_AVATAR_SIZE_KB * 1024 and quality > 40:
            quality -= 5
            img.save(self.avatar.path, optimize=True, quality=quality)

    def delete(self, *args, **kwargs):
        if self.avatar and os.path.isfile(self.avatar.path):
            os.remove(self.avatar.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Service(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    time_for_servicing = models.PositiveIntegerField(default=0, help_text="Additional time for servicing after the appointment in minutes")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    need_staff_confirmation = models.BooleanField(default=False)
    restrict_to_available_dates = models.BooleanField(
        default=False,
        help_text="If checked, this service will only be available on the specified dates below"
    )
    available_dates = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of dates when this service is available (format: YYYY-MM-DD). Max 10 dates."
    )

    def __str__(self):
        return f"{self.name} — {self.company.name}"


class WorkingHours(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="working_hours")
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_day_off = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.company.name} — {self.get_day_of_week_display()}"


class CompanyImage(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=company_img_upload)
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']

    MAX_IMAGE_SIZE_KB = 300
    MAX_DIMENSIONS = (1000, 1000)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image:
            self._optimize_image()

    def _optimize_image(self):
        img = Image.open(self.image.path)
        img.thumbnail(self.MAX_DIMENSIONS, Image.Resampling.LANCZOS)
        quality = 85
        img.save(self.image.path, optimize=True, quality=quality)

        while os.path.getsize(self.image.path) > self.MAX_IMAGE_SIZE_KB * 1024 and quality > 40:
            quality -= 5
            img.save(self.image.path, optimize=True, quality=quality)

    def __str__(self):
        return f"{self.company.name} - Image {self.id}"

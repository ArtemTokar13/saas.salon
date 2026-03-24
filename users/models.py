from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from app.constants import COUNTRY_CHOICES
from companies.models import Company, Staff


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255, blank=True)
    country_code = models.CharField(max_length=10, blank=True, null=True, choices=COUNTRY_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return self.user.username


# Signal to automatically create UserProfile when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


class DailyVisit(models.Model):
    ip = models.GenericIPAddressField()
    date = models.DateField()

    class Meta:
        unique_together = ('ip', 'date')
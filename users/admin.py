from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'company', 'is_admin', 'created_at']
    list_filter = ['is_admin', 'company', 'created_at']
    search_fields = ['user__username', 'full_name', 'phone_number']

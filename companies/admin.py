from django.contrib import admin
from .models import Company, Staff, Service, WorkingHours, CompanyImage


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'administrator', 'created_at']
    search_fields = ['name', 'city', 'email']
    list_filter = ['city', 'created_at']


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'specialization', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['name', 'specialization']
    filter_horizontal = ['services']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'duration', 'price', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['name']


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ['company', 'day_of_week', 'start_time', 'end_time', 'is_day_off']
    list_filter = ['company', 'day_of_week', 'is_day_off']


@admin.register(CompanyImage)
class CompanyImageAdmin(admin.ModelAdmin):
    list_display = ['company', 'caption', 'order', 'created_at']
    list_filter = ['company', 'created_at']

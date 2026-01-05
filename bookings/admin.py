from django.contrib import admin
from .models import Customer, Booking


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email']
    search_fields = ['name', 'phone', 'email']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['customer', 'company', 'service', 'staff', 'date', 'start_time', 'duration', 'price', 'status', 'created_at']
    list_filter = ['company', 'status', 'date', 'created_at']
    search_fields = ['customer__name', 'customer__phone']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'confirmed_at', 'confirmed_by', 'delete_code']
    fieldsets = (
        ('Booking Info', {
            'fields': ('company', 'customer', 'service', 'staff', 'date', 'start_time', 'end_time')
        }),
        ('Details', {
            'fields': ('duration', 'price', 'status')
        }),
        ('Confirmation', {
            'fields': ('confirmed_at', 'confirmed_by'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('created_at', 'delete_code'),
            'classes': ('collapse',)
        }),
    )


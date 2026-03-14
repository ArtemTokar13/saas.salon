from django.contrib import admin
from .models import WhatsAppConversation, WhatsAppMessage, PendingBooking


@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'current_state', 'company', 'customer', 'last_message_at']
    list_filter = ['current_state', 'created_at']
    search_fields = ['phone_number', 'customer__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer', 'company')


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'direction', 'from_number', 'message_body_short', 'created_at']
    list_filter = ['direction', 'created_at']
    search_fields = ['from_number', 'to_number', 'message_body']
    readonly_fields = ['created_at']
    
    def message_body_short(self, obj):
        return obj.message_body[:50] + '...' if len(obj.message_body) > 50 else obj.message_body
    message_body_short.short_description = 'Message'


@admin.register(PendingBooking)
class PendingBookingAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'company', 'service', 'booking_date', 'booking_time', 'created_booking']
    list_filter = ['created_at', 'booking_date']
    search_fields = ['customer_name', 'service_name']
    readonly_fields = ['created_at', 'updated_at']
